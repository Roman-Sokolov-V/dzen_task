from django.core.cache import cache
from rest_framework import viewsets, generics, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from comments.models import Comment
from comments.serializers import (
    CommentCreateSerializer, CommentRootListSerializer, CommentWithDescendantsSerializer, BasicCommentSerializer
)
import logging

logger = logging.getLogger(__name__)

class CommentViewSet(viewsets.ModelViewSet):
    """
    list -  повертає пагінований список корeневих коментарів, з підтримкою ордерінгу за author__username, "reated_at, author__email
    retrieve - повертає окремий коментар
    tree -  повертає окремий коментар з древом відповідей
    """
    queryset = Comment.objects.all()
    permission_classes = (AllowAny,)
    authentication_classes = []
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("author__username", "created_at", "author__email")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "list":
            return Comment.objects.root_nodes().select_related('author')
        if self.action == "retrieve":
            return queryset.select_related('author')
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return CommentRootListSerializer
        if self.action == "create":
            return CommentCreateSerializer
        if self.action == "retrieve":
            return BasicCommentSerializer
        if self.action == "tree":
            return CommentWithDescendantsSerializer
        else:
            return BasicCommentSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=True, url_path='tree')
    def tree(self, request, pk=None):
        """Returns the comment and all replies in the form of a tree (Cached)"""
        cache_key = f"comment_tree_{pk}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info("##############################################################")
            logger.info("-------------------------Cache found--------------------------")
            return Response(cached_data)

        comment = self.get_object()
        serializer = self.get_serializer(comment, many=False, context={'request': request})
        data = serializer.data
        cache.set(cache_key, data, timeout=900)
        return Response(data)

    def _invalidate_comment_tree_cache(self, comment):
        """Очищає кеш для поточного коментаря та всіх його батьків аж до кореня"""
        # Скидаємо кеш для самого коментаря
        cache.delete(f"comment_tree_{comment.id}")

        # Якщо у коментаря є батьки, їхні дерева теж змінилися, тому їх треба інвалідувати
        for ancestor in comment.get_ancestors():
            cache.delete(f"comment_tree_{ancestor.id}")

    def perform_create(self, serializer):
        comment = serializer.save()
        self._invalidate_comment_tree_cache(comment)

    def perform_update(self, serializer):
        comment = serializer.save()
        self._invalidate_comment_tree_cache(comment)

    def perform_destroy(self, instance):
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
#
# class CommentRetrieveView(generics.RetrieveAPIView):
#     queryset = Comment.objects.all()
#     permission_classes = (AllowAny,)
#     authentication_classes = []
#     serializer_class = BasicCommentSerializer

