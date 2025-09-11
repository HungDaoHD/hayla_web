# import os
# from dotenv import load_dotenv
# from email.message import EmailMessage
# from aiosmtplib import SMTP





# class Mailer:

#     def __init__(self):
#         try:
#             load_dotenv()

#             self.SMTP_HOST = os.environ.get("SMTP_HOST")
#             self.SMTP_PORT = int(os.environ.get("SMTP_PORT"))
#             self.SMTP_USER = os.environ.get("SMTP_USER")
#             self.SMTP_PASSWORD  = os.environ.get("SMTP_PASSWORD")
            
            
#             if not self.SMTP_HOST:
#                 raise RuntimeError('SMTP_HOST must be set')

#             elif not self.SMTP_PORT:
#                 raise RuntimeError('SMTP_PORT must be set')
            
#             elif not self.SMTP_USER:
#                 raise RuntimeError('SMTP_USER must be set')
            
#             elif not self.SMTP_PASSWORD:
#                 raise RuntimeError('SMTP_PASSWORD must be set')
            
            
            
            
            
#         except Exception as err:
#             raise err

    
#     async def send_email(self):
        
#         MAIL_FROM = self.SMTP_USER
        
#         msg = EmailMessage()
#         msg["From"] = MAIL_FROM
#         msg["To"] = MAIL_FROM
#         msg["Subject"] = "Test via gmail SMTP"
#         msg.set_content("Hello from gmail SMTP!")
        
#         async with SMTP(hostname=self.SMTP_HOST, port=self.SMTP_PORT, start_tls=True, timeout=30) as smtp:
#             await smtp.login(self.SMTP_USER, self.SMTP_PASSWORD)
#             await smtp.send_message(msg)




# mailer = Mailer()


