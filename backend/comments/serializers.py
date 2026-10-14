from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from comments.models import Comment
from comments.validators import validate_txt_file
from user.serializers import UserSerializer
from utils import resize_image


class BasicCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for basic comment representation.
    Includes id, author, content, creation date, image, and file.
    """

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
    """
    Serializer for creating a comment.
    Includes read-only fields for id and author (username).
    """
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
    email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "email", "content", "image", "file", "created_at"]
        read_only_fields = ["id", "author", "email", "content", "image", "file", "created_at"]


class CommentFlatSerializer(serializers.ModelSerializer):
    """
    Serializer for a flat comment representation used in trees.
    Includes author's username and reply count.
    """
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
    """
    Serializer for a comment with its descendants (tree).
    Includes author's username, reply count, and nested replies.
    """
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
        """
        Return a list of replies (descendants) for the comment.
        Builds a tree structure from the descendants.
        """
        # 1. Get all descendants in a single query
        descendants = (
            obj.get_descendants().select_related("author").order_by("tree_id", "lft")
        )

        comment_map = {}
        for child in descendants:
            data = CommentFlatSerializer(child, context=self.context).data
            data["replies"] = []  # Add an empty list for future children
            comment_map[child.id] = data

        tree = []
        for child in descendants:
            node = comment_map[child.id]
            if child.parent_id == obj.id:  # if the node is a direct child
                tree.append(node)
            elif (
                child.parent_id in comment_map
            ):  # if the node is a reply to another child (grandchild, etc.)
                comment_map[child.parent_id]["replies"].append(node)
        return tree


class CommentActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for comment activity via WebSocket.
    Includes id, author, content, creation date, image, file, and parent.
    """
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)
    image = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at", "image", "file", "parent"]

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_file(self, obj):
        if obj.file:
            return obj.file.url
        return None