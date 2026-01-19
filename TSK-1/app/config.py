import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # База SQLite создастся файлом рядом с проектом
    SQLALCHEMY_DATABASE_URI = "sqlite:///ads.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False  # чтобы кириллица нормально отображалась
