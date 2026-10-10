from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from app.settings import MAX_DEPTH_REPLIES_COMMENT, MAX_DEPTH_COMMENTS
from comments.models import Comment
from user.serializers import UserSerializer


class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

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

    def get_author(self, obj):
        """
        Get the author from the cache, if not in the cache we get it from the database and add it to the cache.
        Return the author (User)
        """
        if not obj.author_id:
            return None
        users_cache = self.context.setdefault('users_cache', {})
        if obj.author_id not in users_cache:
            users_cache[obj.author_id] = UserSerializer(obj.author).data
        return users_cache[obj.author_id]

    def get_replies_count(self, obj):
        """We get the total number of all descendants (MPTT does this without an additional SQL query)"""
        return obj.get_descendant_count()

    def get_replies(self, obj, max_depth_comment=MAX_DEPTH_COMMENTS):
        children = obj.get_children()
        if max_depth_comment:
            # Обмежуємо глибину рекурсії
            max_depth = self.context.get('max_depth', max_depth_comment)
            if max_depth <= 1:
                return []
            next_context = self.context.copy()
            next_context['max_depth'] = max_depth - 1
            # Отримуємо дітей поточного вузла

            return CommentTreeChildSerializer(children, many=True, context=next_context).data
        return CommentTreeChildSerializer(children, many=True, context=self.context).data




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
    def get_replies(self, obj, max_depth_comment=MAX_DEPTH_REPLIES_COMMENT):
        return super().get_replies(obj, max_depth_comment)


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = [
            'author',
            'content',
            'image',
            'file',
            'parent',
        ]


class CommentRootListSerializer(serializers.ModelSerializer):
    author = serializers.SlugRelatedField(slug_field='username', read_only=True)
    class Meta:
        model = Comment
        fields = [
            'author',
            'content',
            'image',
            'file',
            "created_at"
        ]