from django.urls import path
from rest_framework import routers

from comments.views import CommentViewSet

app_name = 'comments'

router = routers.DefaultRouter()
router.register(r'', CommentViewSet)
urlpatterns = [
] + router.urls

