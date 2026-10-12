from celery import shared_task
from notification.email_notification import send_reply_notification

@shared_task
def task_send_reply_notification(subject, message, from_email, to_email):
    print(f"Задача надсилання повідомлення в чергу")
    send_reply_notification(subject, message, from_email, to_email)