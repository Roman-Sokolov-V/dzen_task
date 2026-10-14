print("CONSUMERS.PY LOADED - PRINT STATEMENT AT TOP OF FILE", flush=True)
import asyncio
import logging
from django.contrib.auth import get_user_model

from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework import permissions
from djangochannelsrestframework.observer import model_observer
from djangochannelsrestframework.pagination import WebsocketLimitOffsetPagination
from rest_framework import filters, status
from django.core.cache import cache
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async

from comments.models import Comment
from comments.serializers import CommentCreateSerializer, CommentRootListSerializer, CommentWithDescendantsSerializer, CommentActivitySerializer

logger = logging.getLogger(__name__)


class CommentConsumer(GenericAsyncAPIConsumer):
    # We want to allow any user to connect for listening, but require authentication for modifications.
    # We'll override the permission classes per action if needed.
    permission_classes = [permissions.AllowAny]

    async def connect(self):
        # Check if the user is authenticated (optional for listening)
        self.user = self.scope["user"]
        # Accept the connection
        await self.accept()
        # Send the initial list of root comments
        await self.send_initial_comments()

    async def disconnect(self, close_code):
        # Leave the room
        pass

    async def send_initial_comments(self):
        # Fetch root comments (those with parent=None)
        # We'll use the same queryset as the CommentViewSet list action.
        queryset = Comment.objects.root_nodes().select_related("author")
        # Evaluate the queryset in a thread-safe manner for async context
        queryset_list = await database_sync_to_async(list)(queryset)
        # Serialize the data
        serializer = CommentRootListSerializer(queryset_list, many=True)
        # Send the data to the client
        await self.send_json({
            "action": "initial_comments",
            "data": serializer.data
        })

    # We'll use the model_observer to broadcast changes to the Comment model.
    @model_observer(Comment)
    async def comment_activity(self, message, action, observer, **kwargs):
        # This method is called when a Comment instance is created, updated, or deleted.
        # We need to send a message to the client.
        # Determine the type of action and serialize the instance appropriately.
        # For simplicity, we'll send the comment data using CommentRootListSerializer for root comments
        # and for replies we might need to send the whole tree? But let's just send the comment itself.
        # However, the requirement is to update the comment list. We'll send the comment and let the client handle it.
        # We'll also need to know if the comment is a root or a reply to update the UI correctly.
        # For now, we'll send the comment with its basic data and let the client decide.

        # We'll serialize the comment using CommentRootListSerializer if it's a root, otherwise we might need a different serializer.
        # But note: the client expects to see the comment in the list of root comments or in the replies of a parent.
        # We'll send the comment and the client can decide where to put it.

        # Let's use the CommentWithDescendantsSerializer for the comment? That might be too heavy.
        # Instead, we'll send the comment data using a serializer that includes the necessary fields for the UI.
        # We'll create a simple serializer for the activity or reuse CommentRootListSerializer for root comments and for replies we can use the same?
        # But note: the CommentRootListSerializer does not include the parent field, which is important for replies.

        # We'll use the CommentCreateSerializer for activity? It includes parent.

        # However, we don't want to expose the ability to create via the websocket? We'll handle creation separately.

        # For activity, we'll send the comment data using CommentRootListSerializer for root comments and for replies we'll send a serializer that includes parent.
        # Let's create a serializer for the activity that includes: id, author (username), content, created_at, image, file, parent (if any), and level.

        # We'll use the CommentFlatSerializer? It includes: id, author, parent, content, created_at, image, file, level, replies_count.
        # But note: the CommentFlatSerializer is used in the tree action.

        # We'll use the CommentFlatSerializer for the activity.

        # However, we must note that the CommentFlatSerializer uses `get_descendant_count` for replies_count, which might be heavy.
        # We can avoid that by using a simple serializer.

        # Let's create a temporary serializer for the activity.

        # But to keep it simple, we'll use the CommentWithDescendantsSerializer without the replies? That doesn't make sense.

        # Alternatively, we can send the comment's ID and let the client fetch the updated comment via API?
        # But the requirement is to update via websocket.

        # We'll send the minimal data needed: id, author (username), content, created_at, image, file, parent_id.

        # We'll do:
        #   data = {
        #       "id": instance.id,
        #       "author": instance.author.username,
        #       "content": instance.content,
        #       "created_at": instance.created_at,
        #       "image": instance.image.url if instance.image else None,
        #       "file": instance.file.url if instance.file else None,
        #       "parent_id": instance.parent_id,
        #   }

        # However, we must be cautious about the image and file URLs.

        # Let's use the same method as in the serializers.

        # We'll serialize the instance using a serializer that we define for the activity.

        # We'll create a serializer class inside the method for simplicity.

        # Serialize the instance using the CommentActivitySerializer
        serializer = CommentActivitySerializer(instance)
        # Determine the action type: create, update, delete
        # We'll send the action and the data.
        await self.send_json({
            "action": action,  # This will be 'create', 'update', or 'delete'
            "data": serializer.data
        })

    # We'll also allow the client to send a message to create a comment.
    async def receive_json(self, content, **kwargs):
        # Expect the content to have an "action" field.
        action = content.get("action")
        if action == "create_comment":
            # Check if the user is authenticated
            if not self.user.is_authenticated:
                await self.send_json({
                    "action": "error",
                    "message": "Authentication required to create a comment."
                })
                return
            # Validate and create the comment using the CommentCreateSerializer.
            serializer = CommentCreateSerializer(data=content.get("data", {}))
            if serializer.is_valid():
                # Save the comment with the current user as author.
                comment = serializer.save(author=self.user)
                # Invalidate the comment tree cache (as done in the ViewSet)
                await sync_to_async(self._invalidate_comment_tree_cache)(comment)
                # The model_observer will pick up the create event and broadcast it.
            else:
                await self.send_json({
                    "action": "error",
                    "message": "Invalid data",
                    "errors": serializer.errors
                })
        else:
            # Ignore unknown actions
            pass

    def _invalidate_comment_tree_cache(self, comment):
        """
        Invalidate the comment tree cache for the comment and all its ancestors.
        """
        # Invalidate cache for the comment itself
        cache.delete(f"comment_tree_{comment.id}")

        # If the comment has ancestors, their trees have changed as well
        for ancestor in comment.get_ancestors():
            cache.delete(f"comment_tree_{ancestor.id}")
