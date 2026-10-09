from django.urls import path
from rest_framework import routers

from comments.views import CommentViewset

app_name = 'comments'

router = routers.DefaultRouter()
router.register(r'', CommentViewset)
urlpatterns = [

] + router.urls

