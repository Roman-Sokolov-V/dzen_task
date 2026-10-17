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
    CommentActivitySerializer,
)

logger = logging.getLogger(__name__)

ALLOWED_COMMENT_ORDERINGS = {
    "author__username",
    "-author__username",
    "created_at",
    "-created_at",
    "author__email",
    "-author__email",
}


def normalize_comment_ordering(ordering):
    if isinstance(ordering, str) and ordering in ALLOWED_COMMENT_ORDERINGS:
        return ordering
    return "-created_at"


class CommentConsumer(GenericAsyncAPIConsumer):
    """
    Asynchronous WebSocket Consumer for managing comments in real-time.
    Uses the djangochannelsrestframework (DCRF) library.
    """

    permission_classes = [permissions.AllowAny]

    async def connect(self):
        """
        Called automatically whenever a new client establishes a
        WebSocket connection with the server (e.g., opens a post page).
        """
        self.user = self.scope["user"]
        await self.accept()

        # Initialize pagination and ordering state for this connection
        self.current_ordering = "-created_at"
        self.current_offset = 0
        self.current_limit = (
            None  # Will be set to PAGE_SIZE if None in send_initial_comments
        )

        # Subscribe the client to the model observer for real-time updates
        await self.comment_activity.subscribe()

        # Send the initial list of root comments
        await self.send_initial_comments()

    async def disconnect(self, close_code):
        """
        Called when the client closes the page or loses the connection.
        """
        await self.comment_activity.unsubscribe()

    async def send_initial_comments(self):
        """
        Loads and sends the client the initial list of root comments
        considering the current sorting and pagination.
        """
        # Import DRF settings to get PAGE_SIZE
        from rest_framework.settings import api_settings

        limit = (
            self.current_limit
            if self.current_limit is not None
            else api_settings.PAGE_SIZE
        )

        # Fetch root comments (parent=None) and apply ordering
        queryset = (
            Comment.objects.root_nodes()
            .select_related("author")
            .order_by(self.current_ordering)
        )
        queryset_list = await database_sync_to_async(list)(queryset)

        # Apply pagination
        paginated_list = queryset_list[
            self.current_offset : self.current_offset + limit
        ]

        # Serialize the data
        serializer = CommentRootListSerializer(paginated_list, many=True)

        # Send to client via websocket
        await self.send_json(
            {
                "action": "initial_comments",
                "data": serializer.data,
                "limit": limit,
                "has_more": self.current_offset + len(paginated_list)
                < len(queryset_list),
            }
        )

    # ==========================================
    # MODEL OBSERVER (REAL-TIME UPDATES)
    # ==========================================
    @model_observer(Comment)
    async def comment_activity(self, message, action, observer, **kwargs):
        """
        Triggered automatically in real-time on CREATE, UPDATE, DELETE of comments.
        """
        await self.send_json({"action": action, "data": message})

    @comment_activity.serializer
    def comment_activity_serialize(self, instance, action, **kwargs):
        """
        Serializes the Comment model instance using CommentActivitySerializer.
        """
        return CommentActivitySerializer(instance).data

    # ==========================================
    # HANDLING MESSAGES FROM CLIENT
    # ==========================================
    async def receive_json(self, content, **kwargs):
        """
        Handles incoming actions from the client via WebSocket (creating a comment, changing sorting, etc.).
        """
        action = content.get("action")

        if action == "change_ordering":
            # Allow the client to switch the root comments sorting "on the fly"
            ordering = content.get("ordering", "-created_at")
            self.current_ordering = normalize_comment_ordering(ordering)
            self.current_offset = 0  # Reset offset to first page
            await self.send_initial_comments()

        elif action == "fetch_paginated_comments":
            # Get pagination and sorting parameters
            limit = content.get("limit", self.current_limit)
            offset = content.get("offset", self.current_offset)
            # Update stored pagination state
            self.current_limit = limit
            self.current_offset = offset
            await self.send_initial_comments()

        elif action == "create_comment":
            # Check authentication
            if not self.user.is_authenticated:
                await self.send_json(
                    {
                        "action": "error",
                        "message": "Authentication required to create a comment.",
                    }
                )
                return

            # Validation and saving
            serializer = CommentCreateSerializer(data=content.get("data", {}))

            if serializer.is_valid():
                comment = await database_sync_to_async(serializer.save)(
                    author=self.user
                )

                # Clear comment lists and tree cache
                await sync_to_async(self._invalidate_comment_tree_cache)(comment)
            else:
                await self.send_json(
                    {
                        "action": "error",
                        "message": "Invalid data",
                        "errors": serializer.errors,
                    }
                )

        else:
            pass

    # ==========================================
    # CACHE INVALIDATION LOGIC
    # ==========================================
    def _invalidate_comment_tree_cache(self, comment):
        """
        Clears the Redis cache when adding or modifying a comment.
        """
        # 1. Clear variations of the root list cache for the main orderings - VIMED PER REQUIREMENT
        # cache.delete("root_comments_list_-created_at")
        # cache.delete("root_comments_list_created_at")

        # 2. Clear the cache for the specific comment tree by its ID (sorting does not affect it)
        cache.delete(f"comment_tree_{comment.id}")

        # 3. Clear the cache for all ancestors in the MPTT tree
        for ancestor in comment.get_ancestors():
            cache.delete(f"comment_tree_{ancestor.id}")
