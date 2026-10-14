import logging
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework import permissions
from djangochannelsrestframework.observer import model_observer

from django.core.cache import cache
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async

from comments.models import Comment
from comments.serializers import (
    CommentCreateSerializer,
    CommentRootListSerializer,
    CommentActivitySerializer
)

logger = logging.getLogger(__name__)


class CommentConsumer(GenericAsyncAPIConsumer):
    """
    Асинхронний WebSocket Consumer для управління коментарями в реальному часі.
    Використовує бібліотеку djangochannelsrestframework (DCRF).
    """
    permission_classes = [permissions.AllowAny]

    async def connect(self):
        """
        Викликається автоматично щоразу, коли новий клієнт встановлює
        WebSocket-з'єднання з сервером (наприклад, відкриває сторінку поста).
        """
        # Зберігаємо поточного користувача зі scope (передається через аутентификацію)
        self.user = self.scope["user"]

        # Приймаємо рукостискання (handshake) і встановлюємо з'єднання
        await self.accept()

        # 1. ОБОВ'ЯЗКОВО підписуємо клієнта на модельний обзервер.
        # Без цього рядочка клієнт не отримуватиме жодних оновлень у реальному часі!
        await self.comment_activity.subscribe()

        # 2. Одразу після підключення відправляємо клієнту початковий список коментарів
        await self.send_initial_comments()

    async def disconnect(self, close_code):
        """
        Викликається, коли клієнт закриває сторінку або втрачає з'єднання.
        """
        # Примусово відписуємося від обзервера (хоча Channels зазвичай робить це сам)
        await self.comment_activity.unsubscribe()

    async def send_initial_comments(self):
        """
        Завантажує та відправляє клієнту початковий список кореневих коментарів.
        Спочатку перевіряє кеш Redis, якщо там пусто — робить запит до БД і кешує результат.
        """
        cache_key = "root_comments_list"

        # Спробуємо отримати список із кешу асинхронно, щоб не блокувати Event Loop
        queryset_list = await sync_to_async(cache.get)(cache_key)

        if queryset_list is None:
            # Якщо в кеші нічого немає, робимо оптимізований запит до бази даних
            # root_nodes() витягує тільки кореневі коментарі (parent=None), select_related підтягує авторів
            queryset = Comment.objects.root_nodes().select_related("author")

            # Перетворюємо QuerySet на звичайний список у безпечному синхронному потоці
            queryset_list = await database_sync_to_async(list)(queryset)

            # Зберігаємо отриманий список у кеш Redis на 15 хвилин (900 секунд)
            await sync_to_async(cache.set)(cache_key, queryset_list, 900)

        # Серіалізуємо дані у форматі JSON для відправки
        serializer = CommentRootListSerializer(queryset_list, many=True)

        # Відправляємо клієнту через вебсокет
        await self.send_json({
            "action": "initial_comments",
            "data": serializer.data
        })

    # ==========================================
    # МОДЕЛЬНИЙ ОБЗЕРВЕР (REAL-TIME ОНОВЛЕННЯ)
    # ==========================================
    @model_observer(Comment)
    async def comment_activity(self, message, action, observer, **kwargs):
        """
        Цей метод спрацьовує автоматично в реальному часі щоразу,
        коли в таблиці Comment відбувається CREATE (створення),
        UPDATE (оновлення) або DELETE (видалення).
        Він розсилає зміни всім підключеним клієнтам.
        """
        await self.send_json({
            "action": action,  # Передаємо тип події: 'create', 'update' або 'delete'
            "data": message  # Дані, які підготував метод-серіалізатор нижче
        })

    @comment_activity.serializer
    def comment_activity_serialize(self, instance, action, **kwargs):
        """
        Допоміжний декоратор для DCRF. Він перетворює об'єкт моделі Comment
        у стандартний словник за допомогою CommentActivitySerializer перед тим,
        як передати його в метод comment_activity вище.
        """
        return CommentActivitySerializer(instance).data

    # ==========================================
    # ОБРОБКА ПОВІДОМЛЕНЬ ВІД КЛІЄНТА
    # ==========================================
    async def receive_json(self, content, **kwargs):
        """
        Цей метод викликається, коли клієнт надсилає на сервер якесь повідомлення
        через WebSocket (наприклад, запит на створення коментаря).
        """
        action = content.get("action")

        if action == "create_comment":
            # Перевіряємо, чи користувач увійшов у систему
            if not self.user.is_authenticated:
                await self.send_json({
                    "action": "error",
                    "message": "Authentication required to create a comment."
                })
                return

            # Валідуємо вхідні дані через спільний Create-серіалізатор
            serializer = CommentCreateSerializer(data=content.get("data", {}))

            if serializer.is_valid():
                # Зберігаємо коментар у базу даних із поточним користувачем як автором
                # (використовуємо database_sync_to_async для безпечної роботи з ORM)
                comment = await database_sync_to_async(serializer.save)(author=self.user)

                # Очищуємо застарілий кеш для дерева коментарів та списків
                await sync_to_async(self._invalidate_comment_tree_cache)(comment)

                # Примітка: метод comment_activity автоматично зловить створення
                # нового коментаря в БД і розішле його всім клієнтам!
            else:
                # Якщо валідація не пройшла — повертаємо помилки клієнту
                await self.send_json({
                    "action": "error",
                    "message": "Invalid data",
                    "errors": serializer.errors
                })
        else:
            # Ігноруємо невідомі дії
            pass

    # ==========================================
    # ЛОГІКА ІНВАЛІДАЦІЇ (СКИНУТЬ) КЕШУ
    # ==========================================
    def _invalidate_comment_tree_cache(self, comment):
        """
        Очищує кеш у Redis, коли створюється або змінюється коментар.
        Це гарантує, що наступні запити не віддадуть застарілу інформацію.
        """
        # 1. Скидаємо загальний кеш списку кореневих коментарів
        cache.delete("root_comments_list")

        # 2. Скидаємо кеш конкретного щойно створеного/зміненого коментаря
        cache.delete(f"comment_tree_{comment.id}")

        # 3. Оскільки це дерево (MPTT), якщо у коментаря є батьківські елементи (предки),
        # їхні гілки теж змінилися — очищуємо кеш і для них також.
        for ancestor in comment.get_ancestors():
            cache.delete(f"comment_tree_{ancestor.id}")