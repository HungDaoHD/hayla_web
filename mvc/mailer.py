import os
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
            
            if not self.SMTP_HOST:
                raise RuntimeError('SMTP_HOST must be set')

            elif not self.SMTP_PORT:
                raise RuntimeError('SMTP_PORT must be set')
            
            elif not self.SMTP_USERNAME:
                raise RuntimeError('SMTP_USER must be set')
            
            elif not self.SMTP_PASSWORD:
                raise RuntimeError('SMTP_PASSWORD must be set')
            
            
            
            
            
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
    
    
    
    
    async def send_email(self):
        
        msg = EmailMessage()
        msg["From"] = self.MAIL_FROM
        msg["To"] = self.MAIL_TO
        msg["Subject"] = "Test via gmail SMTP"
        msg.set_content("Hello from gmail SMTP!")
        
        async with SMTP(hostname=self.SMTP_HOST, port=self.SMTP_PORT, start_tls=True, timeout=30) as smtp:
            await smtp.login(self.SMTP_USERNAME, self.SMTP_PASSWORD)
            await smtp.send_message(msg)




mailer = Mailer()


