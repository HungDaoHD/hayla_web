from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=14, deprecated="auto")



class PasswordHashing:


    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)


    @staticmethod
    def verify_password(hashed_pwd: str, plain_pwd: str) -> bool:
        return pwd_context.verify(plain_pwd, hashed_pwd)



# lst_pass = [
#     'tiger.eagle.dolphin2025',
#     'panda.wolf.koala2025',
#     'lion.horse.penguin2025',
#     'fox.rabbit.shark2025',
#     'cat.bear.turtle2025',
#     'falcon.leopard.seal2025',
#     'monkey.whale.deer2025',
# ]


# for p in lst_pass:
#     print(p, PasswordHashing().get_password_hash(p))


