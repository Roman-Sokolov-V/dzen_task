import uuid
import random

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache


class CaptchaGenerateView(APIView):
    """
    Generates a mathematical captcha and stores the answer in the cache.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        answer = str(num1 + num2)

        captcha_key = str(uuid.uuid4())

        # Зберігаємо результат у кеш на 5 хвилин (300 секунд)
        cache.set(f"captcha_{captcha_key}", answer, timeout=3000) # TODO  CHANGE TIMEOUT

        return Response({
            "captcha_key": captcha_key,
            "question": f"Скільки буде {num1} + {num2}?"
        })