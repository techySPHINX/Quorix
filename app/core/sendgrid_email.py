import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient  # type: ignore
from sendgrid.helpers.mail import Mail, From, To, Content  # type: ignore

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

            response = self.client.send(mail)  # type: ignore

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"SendGrid API error: {response.status_code} - {response.body}")
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


email_service: SendGridEmailService = SendGridEmailService()
