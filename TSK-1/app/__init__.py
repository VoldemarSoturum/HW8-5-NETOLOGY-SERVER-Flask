from flask import Flask
from .config import Config
from .models import db
from .routes import ads_bp
from .errors import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # подключаем БД
    db.init_app(app)

    # регистрируем обработчики ошибок
    register_error_handlers(app)

    # регистрируем роуты
    app.register_blueprint(ads_bp)

    # создаём таблицы (упрощённый вариант без миграций)
    with app.app_context():
        db.create_all()
    #Для правильного отображения русских букв в запросах, без этой настройки будем получать Unicode
    app.json.ensure_ascii = False

    return app
