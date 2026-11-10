"""SMTP delivery. Reset credentials are never returned to production callers."""
import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from app.core.config import settings


async def send_password_reset(recipient: str, link: str):
    if settings.APP_ENV in ("test", "testing"):
        return
    if not settings.SMTP_HOST:
        logging.getLogger("uvicorn").error("Password reset delivery unavailable: configure SMTP_HOST")
        return
    message = EmailMessage()
    message["Subject"] = "TourVoice — Đặt lại mật khẩu"
    message["From"] = settings.SMTP_FROM
    message["To"] = recipient
    message.set_content(f"Liên kết có hiệu lực 15 phút, chỉ dùng một lần:\n{link}\nNếu bạn không yêu cầu, hãy bỏ qua email này.")
    def deliver():
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_STARTTLS:
                smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
            smtp.send_message(message)
    try:
        await asyncio.to_thread(deliver)
    except Exception:
        logging.getLogger("uvicorn").exception("Password reset email delivery failed")
