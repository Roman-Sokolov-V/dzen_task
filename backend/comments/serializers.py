from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from comments.models import Comment
from comments.validators import sanitize_comment_html, validate_txt_file
from user.serializers import UserSerializer
from utils import resize_image


class SafeCommentHTMLField(serializers.CharField):
    def to_internal_value(self, data):
        return sanitize_comment_html(super().to_internal_value(data))

    def to_representation(self, value):
        return super().to_representation(sanitize_comment_html(value))


def sanitize_comment_tree(data):
    if isinstance(data, list):
        return [sanitize_comment_tree(item) for item in data]
    if isinstance(data, dict):
        return {
            key: sanitize_comment_html(value)
            if key == "content" and isinstance(value, str)
            else sanitize_comment_tree(value)
            for key, value in data.items()
        }
    return data


class BasicCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for basic comment representation.
    Includes id, author, content, creation date, image, and file.
    """
    avatar = serializers.ImageField(source="author.avatar", read_only=True)
    content = SafeCommentHTMLField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "avatar",
            "content",
            "created_at",
            "image",
            "file",
        ]


class CommentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a comment.
    Includes read-only fields for id and author (username).
    """
    id = serializers.IntegerField(read_only=True)
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    avatar = serializers.ImageField(source="author.avatar", read_only=True)
    content = SafeCommentHTMLField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "avatar",
            "content",
            "image",
            "file",
            "parent",
        ]

    def validate_image(self, image):
        """
        Validate and resize the image if necessary.
        Returns the processed image file.
        """
        if not image:
            return image
        processed_image = resize_image(image)
        return processed_image

    def validate_file(self, file):
        """
        Validate the uploaded text file.
        Returns the file if valid.
        """
        if not file:
            return file
        validate_txt_file(file)
        return file


class CommentRootListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing root comments.
    Shows the author's username.
    """
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    avatar = serializers.ImageField(source="author.avatar", read_only=True)
    email = serializers.EmailField(source="author.email", read_only=True)
    content = SafeCommentHTMLField(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "avatar", "email", "content", "image", "file", "created_at"]
        read_only_fields = ["id", "author", "avatar", "email", "content", "image", "file", "created_at"]


class CommentFlatSerializer(serializers.ModelSerializer):
    """
    Serializer for a flat comment representation used in trees.
    Includes author's username and reply count.
    """
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    avatar = serializers.ImageField(source="author.avatar", read_only=True)
    content = SafeCommentHTMLField(read_only=True)
    replies_count = serializers.IntegerField(
        source="get_descendant_count", read_only=True
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "avatar",
            "parent",
            "content",
            "created_at",
            "image",
            "file",
            "level",
            "replies_count",
        ]


class CommentWithDescendantsSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для отримання дерева відповідей (нащадків) конкретного коментаря.
    Використовує кешування в Redis на рівні окремого ID коментаря.
    """
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    avatar = serializers.ImageField(source="author.avatar", read_only=True)
    content = SafeCommentHTMLField(read_only=True)
    replies = serializers.SerializerMethodField()
    replies_count = serializers.IntegerField(
        source="get_descendant_count", read_only=True
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "avatar",
            "parent",
            "content",
            "created_at",
            "image",
            "file",
            "level",
            "replies_count",
            "replies",
        ]

    def get_replies(self, obj):
        """
        Повертає список відповідей (нащадків) для коментаря.
        Спочатку перевіряє кеш Redis за унікальним id коментаря.
        Якщо в кеші пусто — будує дерево з бази даних і зберігає в кеш.
        """
        cache_key = f"comment_tree_{obj.id}"

        # 1. Спробуємо взяти готове дерево з кешу
        cached_tree = cache.get(cache_key)
        if cached_tree is not None:
            return sanitize_comment_tree(cached_tree)

        # 2. Якщо в кеші немає, робимо єдиний запит до БД за всіма нащадками цього вузла
        descendants = (
            obj.get_descendants().select_related("author").order_by("tree_id", "lft")
        )

        comment_map = {}
        for child in descendants:
            # Використовуємо CommentFlatSerializer для плоского представлення кожного нащадка
            data = CommentFlatSerializer(child, context=self.context).data
            data["replies"] = []  # Готуємо масив під майбутні під-відповіді
            comment_map[child.id] = data

        tree = []
        for child in descendants:
            node = comment_map[child.id]
            if child.parent_id == obj.id:
                # Якщо це пряма відповідь на поточний коментар
                tree.append(node)
            elif child.parent_id in comment_map:
                # Якщо це відповідь на іншу відповідь (вкладеність)
                comment_map[child.parent_id]["replies"].append(node)

        # 3. Зберігаємо побудоване дерево в кеш на 15 хвилин (900 секунд)
        cache.set(cache_key, tree, 900)

        return tree

class CommentActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for comment activity via WebSocket.
    Includes id, author, content, creation date, image, file, and parent.
    """
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    avatar = serializers.ImageField(source="author.avatar", read_only=True)
    content = SafeCommentHTMLField(read_only=True)
    image = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()
    root_id = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "author", "avatar", "content", "created_at", "image", "file", "parent", "root_id"]

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_file(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_root_id(self, obj):
        return obj.get_root().id
