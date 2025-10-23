import os
import httpx
from dotenv import load_dotenv
from email.message import EmailMessage
from aiosmtplib import SMTP
import smtplib, ssl





class Mailer:

    def __init__(self):
        try:
            load_dotenv()

            self.SMTP_HOST = os.getenv("SMTP_HOST")
            self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
            self.SMTP_USERNAME = os.getenv("SMTP_USERNAME")
            self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
            self.MAIL_FROM = os.getenv("MAIL_FROM", self.SMTP_USERNAME)
            self.MAIL_TO = os.getenv("MAIL_TO")
            self.API_KEY = os.getenv("RESEND_API_KEY")
            
            if not self.SMTP_HOST:
                raise RuntimeError('SMTP_HOST must be set')

            elif not self.SMTP_PORT:
                raise RuntimeError('SMTP_PORT must be set')
            
            elif not self.SMTP_USERNAME:
                raise RuntimeError('SMTP_USER must be set')
            
            elif not self.SMTP_PASSWORD:
                raise RuntimeError('SMTP_PASSWORD must be set')
            
            elif not self.API_KEY:
                raise RuntimeError('API_KEY must be set')
            
            
            
        except Exception as err:
            raise err

    
    
    async def send_email_sync(self, subject: str, html_body: str, to_addr: str):
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.MAIL_FROM
        msg["To"] = to_addr
        
        msg.set_content("HTML email required.")
        msg.add_alternative(html_body, subtype="html")

        context = ssl.create_default_context()
        with smtplib.SMTP(host=self.SMTP_HOST, port=self.SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(self.SMTP_USERNAME, self.SMTP_PASSWORD)
            server.send_message(msg)
    
    
    
    
    
    
    @staticmethod
    def normalize_recipients(to_field) -> list[str]:
        """
        Accepts a single string, a comma/semicolon separated string, or a list of strings.
        Returns a clean list of valid addresses or raises ValueError.
        """
        if not to_field:
            raise ValueError("Missing recipient(s)")
        # Turn into a list first
        if isinstance(to_field, str):
            # Allow commas or semicolons
            parts = [p.strip() for p in to_field.replace(";", ",").split(",")]
        elif isinstance(to_field, (list, tuple, set)):
            parts = [str(p).strip() for p in to_field]
        else:
            raise ValueError("Unsupported recipient type")

        # Remove empties and dedupe
        parts = list({p for p in parts if p})

        # Validate with parseaddr (simple, robust)
        cleaned = []
        for p in parts:
            name, addr = parseaddr(p)  # supports "Name <email@x.com>" or "email@x.com"
            if not addr or "@" not in addr or addr.startswith(".") or addr.endswith("."):
                raise ValueError(f"Invalid email address: {p}")
            # basic extra guard for consecutive dots or dot right before @
            local, _, domain = addr.partition("@")
            if not local or not domain or ".." in addr or local.endswith("."):
                raise ValueError(f"Invalid email address: {p}")
            cleaned.append(p)  # keep original "Name <...>" if provided
        return cleaned

    
    
    async def send_email_resend(self, to_addr: str, subject: str, html_body: str):
        # self.API_KEY set in Render
        
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self.API_KEY}"},
                json={
                    "from": "Hayla Web <onboarding@resend.dev>",
                    "to": to_addr,
                    "subject": subject,
                    "html": html_body
                }
            )
            
            print("[RESEND ERROR]", r.status_code, r.text)
            r.raise_for_status()





mailer = Mailer()


