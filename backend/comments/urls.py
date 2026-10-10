from django.urls import path
from rest_framework import routers

from comments.views import CommentViewSet, CommentRootListView

app_name = 'comments'

router = routers.DefaultRouter()
router.register(r'', CommentViewSet)
urlpatterns = [
    path("root/", CommentRootListView.as_view(), name="root-list"),
] + router.urls

