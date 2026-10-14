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

        # Initialize pagination and ordering state for this connection
        self.current_ordering = "-created_at"
        self.current_offset = 0
        self.current_limit = None  # Will be set to PAGE_SIZE if None in send_initial_comments

        # Підписуємо клієнта на модельний обзервер для real-time оновлень
        await self.comment_activity.subscribe()

        # Відправляємо початковий список кореневих коментарів
        await self.send_initial_comments()

    async def disconnect(self, close_code):
        """
        Викликається, коли клієнт закриває сторінку або втрачає з'єднання.
        """
        await self.comment_activity.unsubscribe()

    async def send_initial_comments(self):
        """
        Завантажує та відправляє клієнту початковий список кореневих коментарів
        з урахуванням поточного сортування та пагінації.
        """
        # Імпортуємо налаштування DRF для отримання PAGE_SIZE
        from rest_framework.settings import api_settings
        limit = self.current_limit if self.current_limit is not None else api_settings.PAGE_SIZE

        # Витягуємо кореневі коментарі (parent=None) та сортуємо їх
        queryset = Comment.objects.root_nodes().select_related("author").order_by(self.current_ordering)
        queryset_list = await database_sync_to_async(list)(queryset)

        # Застосовуємо пагінацію
        paginated_list = queryset_list[self.current_offset:self.current_offset + limit]

        # Серіалізуємо дані
        serializer = CommentRootListSerializer(paginated_list, many=True)

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
            self.current_ordering = ordering
            self.current_offset = 0  # Reset offset to first page
            await self.send_initial_comments()

        elif action == "fetch_paginated_comments":
            # Отримуємо параметри пагінації та сортування
            limit = content.get("limit", self.current_limit)
            offset = content.get("offset", self.current_offset)
            # Update stored pagination state
            self.current_limit = limit
            self.current_offset = offset
            await self.send_initial_comments()

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
        # 1. Скидаємо варіації кешу кореневих списків для основних сортувань - VIMED ЗА ВИМОГОЮ
        # cache.delete("root_comments_list_-created_at")
        # cache.delete("root_comments_list_created_at")

        # 2. Скидаємо кеш конкретного дерева гілки за його ID (сортування на нього не впливає)
        cache.delete(f"comment_tree_{comment.id}")

        # 3. Скидаємо кеш для всіх предків (ancestors) у MPTT-дереві
        for ancestor in comment.get_ancestors():
            cache.delete(f"comment_tree_{ancestor.id}")