from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from comments.models import Comment
from comments.validators import validate_txt_file
from user.serializers import UserSerializer
from utils import resize_image


class BasicCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "content",
            "created_at",
            "image",
            "file",
        ]


class CommentCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "content",
            "image",
            "file",
            "parent",
        ]

    def validate_image(self, image):
        if not image:
            return image
        processed_image = resize_image(image)
        return processed_image

    def validate_file(self, file):
        if not file:
            return file
        validate_txt_file(file)
        return file



class CommentRootListSerializer(serializers.ModelSerializer):
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Comment
        fields = ["author", "content", "image", "file", "created_at"]


class CommentFlatSerializer(serializers.ModelSerializer):
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    replies_count = serializers.IntegerField(
        source="get_descendant_count", read_only=True
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "parent",
            "content",
            "created_at",
            "image",
            "file",
            "level",
            "replies_count",
        ]


class CommentWithDescendantsSerializer(serializers.ModelSerializer):
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    replies = serializers.SerializerMethodField()
    replies_count = serializers.IntegerField(
        source="get_descendant_count", read_only=True
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
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
        # 1. Отримуємо всіх нащадків одним запитом
        descendants = (
            obj.get_descendants().select_related("author").order_by("tree_id", "lft")
        )

        comment_map = {}
        for child in descendants:
            data = CommentFlatSerializer(child, context=self.context).data
            data["replies"] = []  # Додаємо порожній список для майбутніх дітей
            comment_map[child.id] = data

        tree = []
        for child in descendants:
            node = comment_map[child.id]
            if child.parent_id == obj.id:  # якщо вузол є безпосереднім нащадком
                tree.append(node)
            elif (
                child.parent_id in comment_map
            ):  # якщо вузол є відповіддю на інший дочірній елемент (внука, правнука тощо)
                comment_map[child.parent_id]["replies"].append(node)
        return tree
