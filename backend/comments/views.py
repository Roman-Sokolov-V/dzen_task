from rest_framework import viewsets, generics, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from comments.models import Comment
from comments.serializers import CommentSerializer, CommentTreeChildSerializer, CommentCreateSerializer, \
    CommentRootListSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().select_related('author')
    permission_classes = (AllowAny,)
    authentication_classes = []

    def get_queryset(self):
        queryset = Comment.objects.all().select_related('author')
        if self.action == "list":
            return queryset.filter(parent=None)
        return queryset

    def get_serializer_class(self):
        if self.action == "get_replies":
            return CommentTreeChildSerializer
        if self.action == "create":
            return CommentCreateSerializer
        else:
            return CommentSerializer

    @action(detail=True, methods=['get'], url_path='replies')
    def get_replies(self, request, pk=None):
        comment = self.get_object()
        # Отримуємо прямих дітей або всіх нащадків
        replies_qs = comment.get_children().select_related('author')
        # Застосовуємо пагінатор ViewSet-а
        page = self.paginate_queryset(replies_qs)
        serializer = self.get_serializer(page, many=True, context=self.get_serializer_context())
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class CommentRootListView(generics.ListAPIView):
    queryset = Comment.objects.root_nodes().select_related('author')
    permission_classes = (AllowAny,)
    authentication_classes = []
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("author__username", "created_at", "author__email")
    ordering = ("-created_at",)
    serializer_class = CommentRootListSerializer