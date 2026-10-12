from django.db.models.signals import post_save
from django.dispatch import receiver


from comments.models import Comment
from app.settings import DEFAULT_FROM_EMAIL
from comments.task import task_send_reply_notification


@receiver(post_save, sender=Comment)
def handle_signal_comment_creation(sender, instance, created, **kwargs):
    if created:
        if instance.parent:
            if instance.parent and instance.parent.author:
                subject = "You have got a new reply to the comment"
                message = f"Yore comment: {instance.parent.content} \n Reply: {instance.content} \n url: <фронд url на цей коментарій>"  # TODO <фронд url на цей коментарій> - input real url
                from_email = DEFAULT_FROM_EMAIL
                to_email = instance.parent.author.email
                task_send_reply_notification.delay(subject, message, from_email, to_email)
