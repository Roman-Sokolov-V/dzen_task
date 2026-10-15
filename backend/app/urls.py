"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os
from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static

from captcha.captcha import CaptchaGenerateView
from . import views  # Import the views from the current app

urlpatterns = [
    path("", views.frontend_index, name="frontend-index"),  # Serve the frontend at the root
    path("admin/", admin.site.urls),
    path("api/user/", include("user.urls")),
    path("api/captcha/", CaptchaGenerateView.as_view(), name="captcha-generate"),
    path("api/comments/", include("comments.urls")),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] + debug_toolbar_urls()


# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Also serve the frontend directory as static files for JS, etc.
    # We'll add an extra directory for the frontend src
    urlpatterns += static('/frontend/', document_root=os.path.join(settings.BASE_DIR, 'frontend'))
