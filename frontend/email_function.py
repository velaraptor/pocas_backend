"""Send Account Recovery Email"""
import os
from flask import render_template
from flask_mail import Message
from frontend.models.flask_models import mail


def send_email(user):
    """Send Email with JWT Token for Password Recovery"""
    token = user.get_reset_token()

    msg = Message()
    msg.subject = "MHP Portal Password Reset"
    msg.sender = os.getenv("MAIL_USERNAME")
    msg.recipients = [user.email]
    msg.html = render_template("reset_email.html", user=user, token=token)
    mail.send(msg)
