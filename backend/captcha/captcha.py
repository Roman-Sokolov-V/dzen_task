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

        # Store the result in cache for 5 minutes (300 seconds)
        cache.set(
            f"captcha_{captcha_key}", answer, timeout=300
        )  # Fixed timeout to 300 seconds (5 minutes)

        return Response(
            {"captcha_key": captcha_key, "question": f"What is {num1} + {num2}?"}
        )