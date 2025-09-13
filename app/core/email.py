import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import emails
from jinja2 import Environment, FileSystemLoader

from .config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.sendgrid_enabled = bool(
            settings.SENDGRID_API_KEY and settings.SENDGRID_FROM_EMAIL
        )
        self.smtp_enabled = bool(
            settings.SMTP_HOST and settings.SMTP_PORT and settings.EMAILS_FROM_EMAIL
        )

        if not (self.sendgrid_enabled or self.smtp_enabled):
            logger.warning("No email service configured. Email notifications disabled.")

        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )

    def _get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration."""
        return {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "tls": settings.SMTP_TLS,
            "user": settings.SMTP_USER,
            "password": settings.SMTP_PASSWORD,
        }

    def _get_sendgrid_config(self) -> Dict[str, Any]:
        """Get SendGrid configuration."""
        return {
            "host": "smtp.sendgrid.net",
            "port": 587,
            "tls": True,
            "user": "apikey",
            "password": settings.SENDGRID_API_KEY,
        }

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> tuple[str, str]:
        try:
            # Render HTML template
            html_template = self.jinja_env.get_template(f"{template_name}.html")
            html_content = html_template.render(**context)

            # Try to render text template, fallback to stripped HTML
            try:
                text_template = self.jinja_env.get_template(f"{template_name}.txt")
                text_content = text_template.render(**context)
            except Exception:
                import re
                text_content = re.sub(r'<[^>]+>', '', html_content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()

            return html_content, text_content
        except Exception as e:
            logger.error(f"Template rendering failed for {template_name}: {e}")
            raise

    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send email with template rendering.

        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Template name (without extension)
            context: Template context variables
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)

        Returns:
            bool: True if email sent successfully
        """
        if not settings.EMAILS_ENABLED:
            logger.info(f"Email disabled. Would send to {to_email}: {subject}")
            return False

        try:
            # Render templates
            html_content, text_content = self._render_template(template_name, context)

            # Determine email configuration
            if self.sendgrid_enabled:
                smtp_config = self._get_sendgrid_config()
                from_email = settings.SENDGRID_FROM_EMAIL
                from_name = settings.SENDGRID_FROM_NAME
            else:
                smtp_config = self._get_smtp_config()
                from_email = settings.EMAILS_FROM_EMAIL
                from_name = settings.EMAILS_FROM_NAME

            # Create email message
            message = emails.html(
                html=html_content,
                text=text_content,
                subject=subject,
                mail_from=(from_email, from_name)
            )

            # Send email
            response = message.send(
                to=to_email,
                cc=cc,
                bcc=bcc,
                smtp=smtp_config
            )

            if response.status_code == 250:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Email send failed to {to_email}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Email send error to {to_email}: {e}")
            return False

    async def send_booking_confirmation(
        self,
        user_email: str,
        user_name: str,
        booking_data: Dict[str, Any]
    ) -> bool:
        """Send booking confirmation email."""
        context = {
            "user_name": user_name,
            "booking_id": booking_data.get("id"),
            "event_name": booking_data.get("event_name"),
            "event_date": booking_data.get("event_date"),
            "event_location": booking_data.get("event_location"),
            "number_of_tickets": booking_data.get("number_of_tickets"),
            "total_price": booking_data.get("total_price"),
            "booking_date": booking_data.get("booked_at"),
            "project_name": settings.PROJECT_NAME,
        }

        return await self.send_email(
            to_email=user_email,
            subject=f"Booking Confirmation - {booking_data.get('event_name')}",
            template_name="booking_confirmation",
            context=context
        )

    async def send_booking_cancellation(
        self,
        user_email: str,
        user_name: str,
        booking_data: Dict[str, Any]
    ) -> bool:
        """Send booking cancellation email."""
        context = {
            "user_name": user_name,
            "booking_id": booking_data.get("id"),
            "event_name": booking_data.get("event_name"),
            "event_date": booking_data.get("event_date"),
            "cancellation_date": booking_data.get("cancelled_at"),
            "refund_info": booking_data.get("refund_info", "Refund will be processed within 5-7 business days."),
            "project_name": settings.PROJECT_NAME,
        }

        return await self.send_email(
            to_email=user_email,
            subject=f"Booking Cancellation - {booking_data.get('event_name')}",
            template_name="booking_cancellation",
            context=context
        )

    async def send_waitlist_notification(
        self,
        user_email: str,
        user_name: str,
        event_data: Dict[str, Any],
        available_tickets: int
    ) -> bool:
        """Send waitlist notification email."""
        context = {
            "user_name": user_name,
            "event_name": event_data.get("name"),
            "event_date": event_data.get("start_date"),
            "event_location": event_data.get("location"),
            "available_tickets": available_tickets,
            "booking_deadline": event_data.get("booking_deadline", "24 hours"),
            "project_name": settings.PROJECT_NAME,
            "booking_url": f"{settings.SERVER_HOST}/events/{event_data.get('id')}/book"
        }

        return await self.send_email(
            to_email=user_email,
            subject=f"Tickets Available - {event_data.get('name')}",
            template_name="waitlist_notification",
            context=context
        )

    async def send_event_reminder(
        self,
        user_email: str,
        user_name: str,
        booking_data: Dict[str, Any],
        hours_until_event: int
    ) -> bool:
        """Send event reminder email."""
        context = {
            "user_name": user_name,
            "event_name": booking_data.get("event_name"),
            "event_date": booking_data.get("event_date"),
            "event_location": booking_data.get("event_location"),
            "number_of_tickets": booking_data.get("number_of_tickets"),
            "hours_until_event": hours_until_event,
            "booking_id": booking_data.get("id"),
            "project_name": settings.PROJECT_NAME,
        }

        return await self.send_email(
            to_email=user_email,
            subject=f"Event Reminder - {booking_data.get('event_name')}",
            template_name="event_reminder",
            context=context
        )


email_service = EmailService()
