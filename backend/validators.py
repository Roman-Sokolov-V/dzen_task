import os
from PIL import Image, UnidentifiedImageError

from rest_framework.exceptions import ValidationError

MAX_IMAGE_WIDTH = 320
MAX_IMAGE_HEIGHT = 240

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}


def validate_image_file(file):
    if file is None:
        return

    extension = os.path.splitext(file.name)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError('Only JPG, JPEG, PNG and GIF images are allowed.')

    try:
        file.seek(0)
        with Image.open(file) as image:
            image.verify()
        file.seek(0)
        with Image.open(file) as image:
            width, height = image.size
    except (OSError, ValueError, UnidentifiedImageError):
        raise ValidationError('Uploaded file is not a valid image.')
    finally:
        file.seek(0)

    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise ValidationError(
            f'Image dimensions must not exceed {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT} pixels.'
        )