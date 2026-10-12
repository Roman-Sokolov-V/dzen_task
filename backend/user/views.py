from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from user.permitions import IsOwnerOrAdmin
from user.serializers import UserRegisterSerializer, UserSerializer

User = get_user_model()


class CreateUserView(CreateAPIView):
    """
    View for user registration.
    Allows any user to create a new account.
    """
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing user profiles.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Return appropriate permission classes based on the action.
        """
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action in ("update", "partial_update", "destroy"):
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """
        Return the serializer class based on the action.
        For retrieve and list, use UserSerializer; otherwise, also UserSerializer.
        """
        if self.action in ("retrieve", "list"):
            return UserSerializer
        return UserSerializer

    def list(self, request, *args, **kwargs):
        """
        Return a list of user profiles.
        """
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Return a specific user profile.
        """
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Update a user profile.
        """
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a user profile.
        """
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a user profile.
        """
        return super().destroy(request, *args, **kwargs)