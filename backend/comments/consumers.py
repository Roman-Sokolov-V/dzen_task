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
        self.user = self.scope["user"]
        await self.accept()

        # Підписуємо клієнта на модельний обзервер для real-time оновлень
        await self.comment_activity.subscribe()

        # Відправляємо початковий список кореневих коментарів із дефолтним сортуванням (нові зверху)
        await self.send_initial_comments(ordering="-created_at")

    async def disconnect(self, close_code):
        """
        Викликається, коли клієнт закриває сторінку або втрачає з'єднання.
        """
        await self.comment_activity.unsubscribe()

    async def send_initial_comments(self, ordering="-created_at"):
        """
        Завантажує та відправляє клієнту початковий список кореневих коментарів
        з урахуванням переданого сортування. Ключ кешу формується динамічно.
        """
        # Формуємо ключ кешу залежно від сортування коренів
        cache_key = f"root_comments_list_{ordering}"

        # Спробуємо отримати список із кешу асинхронно
        queryset_list = await sync_to_async(cache.get)(cache_key)

        if queryset_list is None:
            # Витягуємо кореневі коментарі (parent=None) та сортуємо їх
            queryset = Comment.objects.root_nodes().select_related("author").order_by(ordering)
            queryset_list = await database_sync_to_async(list)(queryset)

            # Зберігаємо у кеш на 15 хвилин (900 секунд)
            await sync_to_async(cache.set)(cache_key, queryset_list, 900)

        # Серіалізуємо дані
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
        Спрацьовує автоматично в реальному часі при CREATE, UPDATE, DELETE коментарів.
        """
        await self.send_json({
            "action": action,
            "data": message
        })

    @comment_activity.serializer
    def comment_activity_serialize(self, instance, action, **kwargs):
        """
        Серіалізує об'єкт моделі Comment за допомогою CommentActivitySerializer.
        """
        return CommentActivitySerializer(instance).data

    # ==========================================
    # ОБРОБКА ПОВІДОМЛЕНЬ ВІД КЛІЄНТА
    # ==========================================
    async def receive_json(self, content, **kwargs):
        """
        Обробляє вхідні дії від клієнта через WebSocket (створення коментаря, зміна сортування тощо).
        """
        action = content.get("action")

        if action == "change_ordering":
            # Дозволяємо клієнту перемикати сортування списку коренів "на льоту"
            ordering = content.get("ordering", "-created_at")
            await self.send_initial_comments(ordering=ordering)

        elif action == "create_comment":
            # Перевіряємо аутентифікацію
            if not self.user.is_authenticated:
                await self.send_json({
                    "action": "error",
                    "message": "Authentication required to create a comment."
                })
                return

            # Валідація та збереження
            serializer = CommentCreateSerializer(data=content.get("data", {}))

            if serializer.is_valid():
                comment = await database_sync_to_async(serializer.save)(author=self.user)

                # Очищуємо кеш списків і дерев
                await sync_to_async(self._invalidate_comment_tree_cache)(comment)
            else:
                await self.send_json({
                    "action": "error",
                    "message": "Invalid data",
                    "errors": serializer.errors
                })
        else:
            pass

    # ==========================================
    # ЛОГІКА ІНВАЛІДАЦІЇ (СКИНУТЬ) КЕШУ
    # ==========================================
    def _invalidate_comment_tree_cache(self, comment):
        """
        Очищує кеш у Redis при додаванні або зміні коментаря.
        """
        # 1. Скидаємо варіації кешу кореневих списків для основних сортувань
        cache.delete("root_comments_list_-created_at")
        cache.delete("root_comments_list_created_at")

        # 2. Скидаємо кеш конкретного дерева гілки за його ID (сортування на нього не впливає)
        cache.delete(f"comment_tree_{comment.id}")

        # 3. Скидаємо кеш для всіх предків (ancestors) у MPTT-дереві
        for ancestor in comment.get_ancestors():
            cache.delete(f"comment_tree_{ancestor.id}")