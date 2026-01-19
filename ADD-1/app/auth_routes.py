"""
Этот файл отвечает за авторизацию пользователей.

Здесь реализовано:
- POST /auth/register  -> регистрация пользователя (создание записи в таблице users)
- POST /auth/login     -> логин пользователя (проверка пароля и выдача JWT токена)

Что важно:
- Пароль НЕ хранится в открытом виде, сохраняется только хэш (password_hash)
- JWT токен нужен для доступа к защищённым эндпоинтам объявлений (создание/редактирование/удаление)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

# db   — объект SQLAlchemy для работы с БД
# User — модель пользователя
from .models import db, User

# ApiError — кастомное исключение для красивых JSON ошибок
from .errors import ApiError

# Blueprint для роутов авторизации
auth_bp = Blueprint("auth", __name__)


# ---------------------------
# POST /auth/register -> регистрация
# ---------------------------
@auth_bp.post("/auth/register")
def register():
    """
    Регистрация нового пользователя.

    Клиент отправляет JSON:
    {
      "email": "user@mail.com",
      "password": "123456"
    }

    Что делает метод:
    1) Проверяет, что запрос содержит JSON-объект
    2) Проверяет валидность email и password
    3) Создаёт объект User
    4) Хэширует пароль через user.set_password()
    5) Пытается сохранить в БД
    6) Если email уже занят — возвращает 409 Conflict
    7) Возвращает данные пользователя без пароля/хэша
    """

    # Пытаемся прочитать JSON из тела запроса.
    # silent=True означает: не выбрасывать исключение при неправильном JSON,
    # а вернуть None, чтобы мы обработали это сами.
    data = request.get_json(silent=True)

    # data обязано быть JSON объектом (dict)
    # если клиент отправил пустой запрос / неправильный JSON / массив / строку -> будет ошибка
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    # Получаем поля из JSON.
    # Используем get(), чтобы не ловить KeyError, если поля нет.
    email = data.get("email")
    password = data.get("password")

    # Валидация email:
    # - должен быть строкой
    # - не должен быть пустым
    # - strip() убирает пробелы в начале/конце
    if not isinstance(email, str) or not email.strip():
        raise ApiError("Field 'email' is required", 400)

    # Валидация password:
    # - должен быть строкой
    # - длина минимум 6 символов (условное правило для ДЗ)
    if not isinstance(password, str) or len(password) < 6:
        raise ApiError("Field 'password' is required (min 6 chars)", 400)

    # Создаём пользователя.
    # email приводим к нижнему регистру, чтобы:
    # "Test@mail.com" и "test@mail.com" считались одним и тем же email
    user = User(email=email.strip().lower())

    # Важно:
    # set_password() НЕ сохраняет пароль как текст,
    # а создаёт password_hash (хэш) через Werkzeug.
    user.set_password(password)

    # Добавляем объект в сессию SQLAlchemy
    db.session.add(user)

    try:
        # Сохраняем в БД
        db.session.commit()
    except IntegrityError:
        # IntegrityError здесь возникает чаще всего из-за unique=True на email,
        # то есть если такой email уже есть в базе.

        # Откатываем транзакцию, иначе сессия останется "сломанной"
        db.session.rollback()

        # 409 Conflict — "конфликт данных" (например email уже зарегистрирован)
        raise ApiError("User with this email already exists", 409)

    # Возвращаем пользователя в формате JSON.
    # В user.to_dict() нет password_hash, это правильно.
    return jsonify(user.to_dict()), 201


# ---------------------------
# POST /auth/login -> логин
# ---------------------------
@auth_bp.post("/auth/login")
def login():
    """
    Логин пользователя (получение JWT токена).

    Клиент отправляет JSON:
    {
      "email": "user@mail.com",
      "password": "123456"
    }

    Что делает метод:
    1) Проверяет, что JSON корректный
    2) Проверяет, что email и password переданы
    3) Находит пользователя по email
    4) Проверяет пароль (через user.check_password())
    5) Если всё верно — создаёт JWT токен
    6) Возвращает токен клиенту

    JWT токен затем используется в заголовке:
      Authorization: Bearer <token>
    """

    # Читаем JSON
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    # Достаём email/password
    email = data.get("email")
    password = data.get("password")

    # Проверяем email
    if not isinstance(email, str) or not email.strip():
        raise ApiError("Field 'email' is required", 400)

    # Проверяем password
    if not isinstance(password, str) or not password:
        raise ApiError("Field 'password' is required", 400)

    # Ищем пользователя в БД по email
    user = User.query.filter_by(email=email.strip().lower()).first()

    # Если пользователь не найден ИЛИ пароль не подходит — возвращаем 401
    # 401 Unauthorized = "неверные учётные данные"
    if not user or not user.check_password(password):
        raise ApiError("Invalid email or password", 401)

    # Создаём JWT токен.
    # В identity кладём user.id (НО обязательно строкой).
    # В Flask-JWT-Extended sub (subject) должен быть строкой,
    # иначе будет ошибка: 422 "Subject must be a string"
    token = create_access_token(identity=str(user.id))

    # Возвращаем токен клиенту.
    # В дальнейшем клиент вставляет его в Authorization header.
    return jsonify({"access_token": token}), 200
