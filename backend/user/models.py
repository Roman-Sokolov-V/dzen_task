from django.db import models
from django.contrib.auth.models import AbstractUser

from validators import validate_image_file


class User(AbstractUser):
    homepage = models.URLField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars', null=True, blank=True, validators=[validate_image_file,])