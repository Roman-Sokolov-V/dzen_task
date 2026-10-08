from django.db import models

from app.settings import AUTH_USER_MODEL
from .validators import validate_html_tags, validate_txt_file, validate_image_file


class Comment(models.Model):
    author = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(
        validators=[validate_html_tags],
        help_text="Коментар з дозволеними HTML-тегами: <a>, <code>, <i>, <strong>"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    image = models.ImageField(
        upload_to='comments/image',
        null=True,
        blank=True,
        validators=[validate_image_file]
    )
    file = models.FileField(
        upload_to='comments/file',
        blank=True,
        validators=[validate_txt_file],
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}"