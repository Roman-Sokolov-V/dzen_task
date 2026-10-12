from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from app.settings import AUTH_USER_MODEL
from comments.validators import validate_html_tags, validate_txt_file
from utils import UniqueFilePath
from validators import validate_image_file


class Comment(MPTTModel):
    author = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(
        validators=[validate_html_tags],
        help_text="Коментар з дозволеними HTML-тегами: <a>, <code>, <i>, <strong>",
    )
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    image = models.ImageField(
        upload_to=UniqueFilePath("comments/images/"),
        null=True,
        blank=True,
        validators=[validate_image_file],
    )
    file = models.FileField(
        upload_to=UniqueFilePath("comments/files/"),
        blank=True,
        null=True,
        validators=[validate_txt_file],
    )

    class MPTTMeta:
        order_insertion_by = ["-created_at"]

    def __str__(self):
        return f"Comment #{self.id} (Author ID: {self.author_id})"
