# utils.py
import os
import uuid
from django.utils.deconstruct import deconstructible
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError


@deconstructible
class UniqueFilePath:
    """
    A class-generator of unique paths for file uploads.
    Using @deconstructible is mandatory for correct operation of Django migrations.
    """

    def __init__(self, subfolder):
        self.subfolder = subfolder

    def __call__(self, instance, filename):
        ext = filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        return os.path.join(self.subfolder, unique_filename)


def resize_image(
    image,
    formats: tuple[str, ...] = ("JPEG", "PNG", "GIF"),
    max_size: tuple[int, int] = (320, 240),
):
    """
    Returns an image file, resizing it according to max_size (320x240),
    preserving proportions, format, and file name.
    Raises ValidationError if the format is invalid or the file is corrupted.
    """
    try:
        img = Image.open(image)
        img_format = img.format.upper() if img.format else None

        # 1. Перевірка формату
        if not img_format or img_format not in [f.upper() for f in formats]:
            raise ValidationError(
                f"Invalid image format. Allowed formats: {', '.join(formats)}"
            )

        # 2. Правильна перевірка орієнтації
        max_w, max_h = max_size
        img_max_side = max(img.width, img.height)
        img_min_side = min(img.width, img.height)
        allowed_max_side = max(max_w, max_h)
        allowed_min_side = min(max_w, max_h)

        # 3. Перевірка, чи потрібно взагалі зменшувати
        if img_max_side > allowed_max_side or img_min_side > allowed_min_side:
            # thumbnail автоматично адаптується під альбомну/портретну орієнтацію
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            buffer = BytesIO()
            save_kwargs = {"format": img_format, "optimize": True}

            # Зберігаємо підтримку анімації для GIF
            if img_format == "GIF" and getattr(img, "is_animated", False):
                save_kwargs["save_all"] = True

            img.save(buffer, **save_kwargs)
            buffer.seek(0)

            # Отримуємо оригінальну назву файлу
            file_name = (
                image.name.split("/")[-1] if hasattr(image, "name") else "upload_image"
            )

            return ContentFile(buffer.read(), name=file_name)

        # Якщо розміри в межах норми — повертаємо оригінал без змін
        return image

    except UnidentifiedImageError, OSError:
        # Якщо файл пошкоджений або це не справжня картинка
        raise ValidationError("The uploaded file is not a valid image or is corrupted.")
