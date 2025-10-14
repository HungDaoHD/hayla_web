import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
# from email.message import EmailMessage
# from aiosmtplib import SMTP


class Database:

    def __init__(self):
        try:
            load_dotenv()

            MONGO_URI = os.getenv('MONGO_URI')
            
            if not MONGO_URI:
                raise RuntimeError('MONGO_URI must be set')

            self.client = AsyncIOMotorClient(MONGO_URI)
            self.hayladb = self.client['hayladb']
            self.clt_user = self.hayladb['user']
            
            print('hayladb connected successfully!!!')

        except Exception as err:
            raise err




mongo_db = Database()


