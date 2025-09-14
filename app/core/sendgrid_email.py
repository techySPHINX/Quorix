import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, From, Mail, To

from .config import settings

logger = logging.getLogger(__name__)


class SendGridEmailService:
    """Production-grade email service using SendGrid API"""

    def __init__(self) -> None:
        self.sendgrid_enabled: bool = bool(
            settings.SENDGRID_API_KEY and settings.SENDGRID_FROM_EMAIL
        )

        if not self.sendgrid_enabled:
            logger.warning("SendGrid not configured. Email notifications disabled.")
        else:
            self.client = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)

        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)), autoescape=True
        )

    def _render_template(
        self, template_name: str, context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Render email templates (HTML and text versions)"""
        try:
            html_template = self.jinja_env.get_template(f"{template_name}.html")
            html_content = html_template.render(**context)

            try:
                text_template = self.jinja_env.get_template(f"{template_name}.txt")
                text_content = text_template.render(**context)
            except Exception:
                import re

                text_content = re.sub(r"<[^>]+>", "", html_content)
                text_content = re.sub(r"\s+", " ", text_content).strip()

            return html_content, text_content
        except Exception as e:
            logger.error(f"Template rendering failed for {template_name}: {e}")
            raise

    async def _send_email_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """Send email using SendGrid API"""
        if not self.sendgrid_enabled:
            logger.info(f"SendGrid disabled. Would send to {to_email}: {subject}")
            return False

        try:
            from_email = From(
                email=settings.SENDGRID_FROM_EMAIL, name=settings.SENDGRID_FROM_NAME
            )
            to_email_obj = To(to_email)

            mail = Mail(
                from_email=from_email,
                to_emails=to_email_obj,
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", text_content),
            )

            if cc:
                for cc_email in cc:
                    mail.add_cc(To(cc_email))

            if bcc:
                for bcc_email in bcc:
                    mail.add_bcc(To(bcc_email))

            response = self.client.send(mail)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(
                    f"SendGrid API error: {response.status_code} - {response.body}"
                )
                return False

        except Exception as e:
            logger.error(f"SendGrid email send failed: {e}")
            return False

    # Example of one typed public method
    async def send_booking_confirmation(
        self, user_email: str, user_name: str, booking_data: Dict[str, Any]
    ) -> bool:
        """Send booking confirmation email"""
        try:
            context = {
                "user_name": user_name,
                "booking_data": booking_data,
                "project_name": settings.PROJECT_NAME,
                "support_email": settings.SENDGRID_FROM_EMAIL,
            }

            html_content, text_content = self._render_template(
                "booking_confirmation", context
            )

            return await self._send_email_sendgrid(
                to_email=user_email,
                subject=f"Booking Confirmation - {booking_data['event_name']}",
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error sending booking confirmation email: {e}")
            return False

    async def send_booking_cancellation(
        self, user_email: str, user_name: str, booking_data: Dict[str, Any]
    ) -> bool:
        """Send booking cancellation email"""
        try:
            context = {
                "user_name": user_name,
                "booking_data": booking_data,
                "project_name": settings.PROJECT_NAME,
                "support_email": settings.SENDGRID_FROM_EMAIL,
            }

            html_content, text_content = self._render_template(
                "booking_cancellation", context
            )

            return await self._send_email_sendgrid(
                to_email=user_email,
                subject=f"Booking Cancellation - {booking_data.get('event_name', '')}",
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error sending booking cancellation email: {e}")
            return False

    async def send_waitlist_notification(
        self,
        user_email: str,
        user_name: str,
        event_data: Dict[str, Any],
        available_tickets: int,
    ) -> bool:
        """Send waitlist notification email"""
        try:
            context = {
                "user_name": user_name,
                "event_data": event_data,
                "available_tickets": available_tickets,
                "project_name": settings.PROJECT_NAME,
            }

            html_content, text_content = self._render_template(
                "waitlist_notification", context
            )

            return await self._send_email_sendgrid(
                to_email=user_email,
                subject=f"Tickets Available - {event_data.get('name', '')}",
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error sending waitlist notification email: {e}")
            return False

    async def send_event_reminder(
        self,
        user_email: str,
        user_name: str,
        booking_data: Dict[str, Any],
        hours_until_event: int = 24,
    ) -> bool:
        """Send event reminder email"""
        try:
            context = {
                "user_name": user_name,
                "booking_data": booking_data,
                "hours_until_event": hours_until_event,
                "project_name": settings.PROJECT_NAME,
            }

            html_content, text_content = self._render_template(
                "event_reminder", context
            )

            return await self._send_email_sendgrid(
                to_email=user_email,
                subject=f"Event Reminder - {booking_data.get('event_name', '')}",
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error sending event reminder email: {e}")
            return False

    async def send_password_reset(
        self, user_email: str, user_name: str, reset_token: str
    ) -> bool:
        """Send password reset email"""
        try:
            context = {
                "user_name": user_name,
                "reset_token": reset_token,
                "project_name": settings.PROJECT_NAME,
            }

            html_content, text_content = self._render_template(
                "password_reset", context
            )

            return await self._send_email_sendgrid(
                to_email=user_email,
                subject="Password Reset Request",
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False

    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email"""
        try:
            context = {
                "user_name": user_name,
                "project_name": settings.PROJECT_NAME,
            }

            html_content, text_content = self._render_template("welcome", context)

            return await self._send_email_sendgrid(
                to_email=user_email,
                subject=f"Welcome to {settings.PROJECT_NAME}",
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        template_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Generic send wrapper: either pass raw html/text or a template_name with context."""
        try:
            if template_name:
                ctx = context or {}
                html_content, text_content = self._render_template(template_name, ctx)
            else:
                if html is None or text is None:
                    raise ValueError(
                        "html and text must be provided when template_name is not used"
                    )
                html_content, text_content = html, text

            return await self._send_email_sendgrid(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
        except Exception as e:
            logger.error(f"Error in send_email wrapper: {e}")
            return False


email_service: SendGridEmailService = SendGridEmailService()
