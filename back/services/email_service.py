import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi.concurrency import run_in_threadpool

from back.config import get_smtp_config
from back.utils.logger import log_error, log_info


class EmailService:
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            # Resolve relative to this file: ../templates/email
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.templates_dir = os.path.join(base_dir, "templates", "email")
        else:
            self.templates_dir = templates_dir

    def _load_template(self, template_name: str) -> str:
        try:
            path = os.path.join(self.templates_dir, template_name)
            # Check if file exists to raise error explicitly if needed, but open handles it
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            # Re-raise or log better context
            log_error(f"Failed to load email template {template_name} from {self.templates_dir}: {e}")
            raise e # Raise to see trace if needed, or return empty handled above

    async def send_email(self, to_email: str, subject: str, html_content: str):
        """
        Sends a real email using SMTP configuration.
        """
        smtp_conf = get_smtp_config()
        
        if not smtp_conf.get("enabled", False):
            log_info(f"SMTP disabled. Email to {to_email} (Subject: {subject}) was NOT sent.")
            return

        host = smtp_conf.get("host")
        port = smtp_conf.get("port", 587)
        user = smtp_conf.get("user")
        password = smtp_conf.get("password")
        from_email = smtp_conf.get("from_email")

        if not all([host, user, password, from_email]):
            log_error("SMTP configuration missing. cannot send email.")
            return

        def _send_sync() -> None:
            try:
                msg = MIMEMultipart()
                msg['From'] = from_email
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(html_content, 'html'))

                # Context manager handles quit
                with smtplib.SMTP(host, port) as server:
                    # server.set_debuglevel(1) # Uncomment for debug
                    server.starttls()
                    server.login(user, password)
                    server.send_message(msg)
                
                log_info(f"Email sent to {to_email} (Subject: {subject})")
            except Exception as e:
                log_error(f"Failed to send email to {to_email}: {e}")
                raise e

        try:
            await run_in_threadpool(_send_sync)
        except Exception as e:
            log_error(f"Async email sending wrapper failed: {e}")
            raise  # Re-raise to inform caller of email failure

    async def send_password_reset_email(self, to_email: str, reset_link: str):
        template = self._load_template("reset_password.html")
        if not template:
            return
        
        content = template.replace("{{ link }}", reset_link)
        await self.send_email(to_email, "Password reset - FableStack", content)

    async def send_magic_login_email(self, to_email: str, magic_link: str):
        template = self._load_template("magic_login.html")
        if not template:
            return

        content = template.replace("{{ link }}", magic_link)
        await self.send_email(to_email, "Magic login - FableStack", content)
