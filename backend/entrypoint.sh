#!/bin/sh

# Зупинити виконання скрипту, якщо якась команда завершиться помилкою
set -e

echo "Застосовуємо міграції..."
python manage.py migrate

# Створення суперюзера
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    python manage.py createsuperuser --noinput
else
    echo "Суперкористувача пропущено: задайте DJANGO_SUPERUSER_USERNAME і DJANGO_SUPERUSER_PASSWORD."
fi
echo "Запускаємо Django сервер..."
exec python manage.py runserver 0.0.0.0:8000