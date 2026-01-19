from flask import Flask

from flask_jwt_extended import JWTManager

from .config import Config
from .models import db
from .routes import ads_bp
from .errors import register_error_handlers

from .auth_routes import auth_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # подключаем БД
    db.init_app(app)

    # регистрируем обработчики ошибок
    register_error_handlers(app)

    # регистрируем роуты
    app.register_blueprint(ads_bp)
    #Роут для регистрации/авторизации
    app.register_blueprint(auth_bp)

    # JWT
    JWTManager(app)

    # создаём таблицы (упрощённый вариант без миграций)
    with app.app_context():
        db.create_all()
    #Для правильного отображения русских букв в запросах, без этой настройки будем получать Unicode
    app.json.ensure_ascii = False

    return app


