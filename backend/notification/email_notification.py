from django.core.mail import send_mail


def send_reply_notification(
        subject: str,
        message: str,
        from_email: str,
        to_email: str,
        **kwargs
):
    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[to_email],
    )