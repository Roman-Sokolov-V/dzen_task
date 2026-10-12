from django.core.cache import cache
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response

from comments.models import Comment
from comments.serializers import (
    CommentCreateSerializer,
    CommentRootListSerializer,
    CommentWithDescendantsSerializer,
    BasicCommentSerializer,
)
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter

from comments.permitions import IsOwner, IsOwnerOrAdmin

logger = logging.getLogger(__name__)


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments.
    """
    queryset = Comment.objects.all()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("author__username", "created_at", "author__email")
    ordering = ("-created_at",)

    def get_permissions(self):
        """
        Return appropriate permission classes based on the action.
        """
        if self.action in ["list", "retrieve", "tree"]:
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated()]
        if self.action in ("update", "partial_update"):
            return [IsOwner()]
        if self.action == "destroy":
            return [IsOwnerOrAdmin()]
        return [IsAdminUser()]

    def get_queryset(self):
        """
        Return the queryset based on the action.
        For list, return root nodes; for retrieve, return all with author select_related.
        """
        queryset = self.queryset
        if self.action == "list":
            return Comment.objects.root_nodes().select_related("author")
        if self.action == "retrieve":
            return queryset.select_related("author")
        return queryset

    def get_serializer_class(self):
        """
        Return the serializer class based on the action.
        """
        if self.action == "list":
            return CommentRootListSerializer
        if self.action == "create":
            return CommentCreateSerializer
        if self.action == "retrieve":
            return BasicCommentSerializer
        if self.action == "tree":
            return CommentWithDescendantsSerializer
        return BasicCommentSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                type=int,
                required=False,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                type=int,
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                description="Which field to use for ordering.",
                type=str,
                enum=["author__username", "-author__username", "created_at", "-created_at", "author__email", "-author__email"],
                required=False,
            )
        ],
        description="Return a paginated list of root comments. Default ordering: -created_at (newest first)."
    )
    def list(self, request, *args, **kwargs):
        """
        Return a paginated list of root comments.
        """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Return a specific comment.
        """
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Create a new comment.
        """
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Update a comment.
        """
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a comment.
        """
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a comment.
        """
        return super().destroy(request, *args, **kwargs)

    @action(methods=["get"], detail=True, url_path="tree")
    def tree(self, request, pk=None):
        """
        Return the comment and all its replies in a tree structure (cached).
        """
        cache_key = f"comment_tree_{pk}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(
                "##############################################################"
            )
            logger.info(
                "-------------------------Cache found--------------------------"
            )
            return Response(cached_data)

        comment = self.get_object()
        serializer = self.get_serializer(
            comment, many=False, context={"request": request}
        )
        data = serializer.data
        cache.set(cache_key, data, timeout=900)
        return Response(data)

    def _invalidate_comment_tree_cache(self, comment):
        """
        Invalidate the comment tree cache for the comment and all its ancestors.
        """
        # Invalidate cache for the comment itself
        cache.delete(f"comment_tree_{comment.id}")

        # If the comment has ancestors, their trees have changed as well
        for ancestor in comment.get_ancestors():
            cache.delete(f"comment_tree_{ancestor.id}")

    def perform_create(self, serializer):
        """
        Save the comment with the current user as author and invalidate the tree cache.
        """
        comment = serializer.save(author=self.request.user)
        self._invalidate_comment_tree_cache(comment)

    def perform_update(self, serializer):
        """
        Save the comment and invalidate the tree cache.
        """
        comment = serializer.save()
        self._invalidate_comment_tree_cache(comment)

    def perform_destroy(self, instance):
        """
        Delete the comment and invalidate the tree cache.
        """
        self._invalidate_comment_tree_cache(instance)
        instance.delete()


# class CommentRootListView(generics.ListAPIView):
#     queryset = Comment.objects.root_nodes().select_related('author')
#     permission_classes = (AllowAny,)
#     authentication_classes = []
#     filter_backends = [filters.OrderingFilter]
#     ordering_fields = ("author__username", "created_at", "author__email")
#     ordering = ("-created_at",)
#     serializer_class = CommentRootListSerializer


# class CommentWithDescendantsView(generics.RetrieveAPIView):
#     queryset = Comment.objects.select_related('author')
#     permission_classes = (AllowAny,)
#     authentication_classes = []
#     serializer_class = CommentWithDescendantsSerializer


# class CommentRetrieveView(generics.RetrieveAPIView):
#     queryset = Comment.objects.all()
#     permission_classes = (AllowAny,)
#     authentication_classes = []
#     serializer_class = BasicCommentSerializer