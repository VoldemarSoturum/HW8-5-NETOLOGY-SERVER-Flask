import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # База SQLite создастся файлом рядом с проектом
    SQLALCHEMY_DATABASE_URI = "sqlite:///ads.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False  # чтобы кириллица нормально отображалась
    #JWT secret, для авторизации/регистрации пользователей (будем хранить в .env)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_dev_key_change_me")