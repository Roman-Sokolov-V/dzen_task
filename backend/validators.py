import os
from PIL import Image, UnidentifiedImageError

from rest_framework.exceptions import ValidationError

from app.settings import MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}


def validate_image_file(file):
    if file is None:
        return

    extension = os.path.splitext(file.name)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Only JPG, JPEG, PNG and GIF images are allowed.")

