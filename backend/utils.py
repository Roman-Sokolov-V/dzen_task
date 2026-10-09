# utils.py
import os
import uuid
from django.utils.deconstruct import deconstructible


@deconstructible
class UniqueFilePath:
    """
    A class-generator of unique paths for file uploads.
    Using @deconstructible is mandatory for correct operation of Django migrations.
    """
    def __init__(self, subfolder):
        self.subfolder = subfolder

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        return os.path.join(self.subfolder, unique_filename)