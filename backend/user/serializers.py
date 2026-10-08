from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'homepage')

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password,])
    homepage = serializers.URLField(write_only=True, required=False, allow_null=True, allow_blank=True)
    captcha_key = serializers.CharField(write_only=True)
    capcha_value = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'homepage','captcha_key', 'capcha_value')

    def validate(self, attrs):
        # Validate CAPTCHA
        captcha_key = attrs.get('captcha_key')
        captcha_value = attrs.get('captcha_value')

        if not captcha_key or not captcha_value:
            raise serializers.ValidationError("CAPTCHA is required.")

        stored_value = cache.get(captcha_key)
        if stored_value is None:
            raise serializers.ValidationError("Invalid or expired CAPTCHA key.")

        if stored_value.lower() != captcha_value.lower():
            raise serializers.ValidationError({"captcha_value": "Invalid CAPTCHA value."})

        # Delete the used CAPTCHA from cache to prevent replay
        cache.delete(captcha_key)

        # Validate that username and email are unique
        username = attrs.get('username')
        email = attrs.get('email')
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError({"username": "A user with that username already exists."})
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "A user with that email already exists."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('captcha_key')
        validated_data.pop('captcha_value')
        password = validated_data.pop('password')

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()