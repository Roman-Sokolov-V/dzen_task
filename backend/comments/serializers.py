from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from app.settings import MAX_DEPTH_COMMENT
from comments.models import Comment


class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'author',
            'parent',
            'content',
            'created_at',
            'image',
            'file',
            'level',
            'replies_count',
            'replies'
        ]

    def get_replies_count(self, obj):
        """We get the total number of all descendants (MPTT does this without an additional SQL query)"""
        return obj.get_descendant_count()

    def get_replies(self, obj):
        """
        If we are at level 0 (root comment), we return only its direct children (level 1 replies)
        """
        if obj.level == 0:
            # get_children() повертає QuerySet дітей 1-го рівня
            children = obj.get_children()
            # Важливо: передаємо context=self.context, щоб зберегти URL-и файлів/картинок
            return CommentChildSerializer(children, many=True, context=self.context).data
        return []


class CommentChildSerializer(serializers.ModelSerializer):
    """Спрощений серіалайзер для відповідей, щоб не робити рекурсію далі 1-го рівня."""
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'author',
            'content',
            'created_at',
            'image',
            'file',
            'parent',
            'level',
            'replies_count'
        ]

    def get_replies_count(self, obj):
        return obj.get_descendant_count()


class CommentTreeChildSerializer(CommentSerializer):
    def get_replies(self, obj):
        # Обмежуємо глибину рекурсії
        max_depth = self.context.get('max_depth', MAX_DEPTH_COMMENT)
        if max_depth <= 1:
            return []
        next_context = self.context.copy()
        next_context['max_depth'] = max_depth - 1

        # Отримуємо дітей поточного вузла
        children = obj.get_children()
        return CommentTreeChildSerializer(children, many=True, context=next_context).data
