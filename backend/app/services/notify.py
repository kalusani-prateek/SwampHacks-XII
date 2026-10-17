"""Outbound notifications: email (SMTP) and SMS (Twilio).

Without SMTP or Twilio settings nothing is sent: each message is saved to the
notifications table with status "logged" (an outbox supervisors can read in
Manage > Briefings). Every attempt, sent or not, is recorded there.
"""
import logging
import smtplib
from email.message import EmailMessage

import requests
from flask import current_app

from ..extensions import db
from ..models import Notification, User

log = logging.getLogger(__name__)


class NotConfigured(Exception):
    """The channel has no credentials, so the message is only logged."""


def send_email(to, subject, body):
    cfg = current_app.config
    if not cfg["SMTP_HOST"]:
        raise NotConfigured
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = cfg["SMTP_FROM"], to, subject
    message.set_content(body)
    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20) as smtp:
        smtp.starttls()
        if cfg["SMTP_USER"]:
            smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        smtp.send_message(message)


def send_sms(to, body):
    cfg = current_app.config
    sid, token, sender = cfg["TWILIO_ACCOUNT_SID"], cfg["TWILIO_AUTH_TOKEN"], cfg["TWILIO_FROM"]
    if not (sid and token and sender):
        raise NotConfigured
    response = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        data={"From": sender, "To": to, "Body": body[:1500]},
        auth=(sid, token),
        timeout=20,
    )
    response.raise_for_status()


def deliver(channel, recipient, subject, body):
    """Try one message and record the outcome (sent / logged / failed)."""
    status, problem = "sent", None
    try:
        if channel == "email":
            send_email(recipient, subject, body)
        else:
            send_sms(recipient, body)
    except NotConfigured:
        status = "logged"
    except Exception as exc:  # network or provider error: keep going, record it
        status, problem = "failed", str(exc)[:500]
        log.warning("%s to %s failed: %s", channel, recipient, exc)
    db.session.add(Notification(channel=channel, recipient=recipient, subject=subject, body=body, status=status, error=problem))


def notify_roles(roles, subject, body, sms_body=None, channels=("email", "sms")):
    """Message every user with one of `roles` on the enabled channels. Returns users reached."""
    users = User.query.filter(User.role.in_(list(roles))).all()
    for user in users:
        if "email" in channels and user.email:
            deliver("email", user.email, subject, body)
        if "sms" in channels and user.phone:
            deliver("sms", user.phone, None, sms_body or subject)
    db.session.commit()
    return len(users)
