"""
Этот файл — набор роутов (эндпоинтов) для работы с объявлениями в Flask REST API.

Здесь реализовано:
- Публичный доступ на чтение:
  - GET /ads           -> список объявлений
  - GET /ads/<id>      -> одно объявление
- Доступ только для авторизованных (JWT):
  - POST /ads          -> создать объявление (владелец = текущий пользователь)
  - PATCH /ads/<id>    -> редактировать (только владелец)
  - DELETE /ads/<id>   -> удалить (только владелец)

Ключевая идея:
- "Владелец" объявления НЕ передаётся в JSON запросе клиентом (чтобы нельзя было подменить владельца),
  а берётся из JWT токена (кто залогинен — тот и владелец).
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

# db — объект SQLAlchemy для работы с базой
# Ad — модель объявления
# User — модель пользователя
from .models import db, Ad, User

# ApiError — наше кастомное исключение, которое превращается в JSON-ответ с нужным HTTP кодом
from .errors import ApiError

# Blueprint — это "модуль роутов".
# Позволяет удобно разделять приложение на части: ads, auth, admin и т.д.
ads_bp = Blueprint("ads", __name__)


def get_current_user() -> User:
    """
    Получаем текущего пользователя из JWT токена.

    Как это работает:
    - Когда пользователь логинится, мы выдаём ему JWT токен.
    - Этот токен клиент отправляет в заголовке:
        Authorization: Bearer <token>
    - Декоратор @jwt_required() проверяет токен.
    - Функция get_jwt_identity() возвращает "identity", которую мы записали в токен
      (обычно это user.id).

    Дальше мы ищем пользователя в базе по этому id.
    Если пользователя нет — значит токен неправильный или пользователь удалён.
    """
    user_id = get_jwt_identity()          # достаём identity из токена
    user = User.query.get(user_id)        # ищем пользователя в базе
    if user is None:
        # 401 — пользователь не авторизован корректно / токен невалидный / user не найден
        raise ApiError("User not found", 401)
    return user


def get_ad_or_404(ad_id: int) -> Ad:
    """
    Получаем объявление по id.

    Если объявление не найдено — возвращаем 404.
    Это стандартное поведение REST API:
      GET /ads/9999 -> 404 Not Found
    """
    ad = Ad.query.get(ad_id)
    if ad is None:
        raise ApiError("Ad not found", 404)
    return ad


# ---------------------------
# GET /ads -> список объявлений (публичный)
# ---------------------------
@ads_bp.get("/ads")
def get_ads():
    """
    Публичный эндпоинт:
    Возвращает список всех объявлений.

    Почему публичный:
    - по условию задания обычно читать объявления можно всем
      (например, как на Avito: смотреть можно без логина).
    """
    # Сортируем по дате создания: новые сверху
    ads = Ad.query.order_by(Ad.created_at.desc()).all()

    # Превращаем объекты Ad в словари через to_dict()
    # jsonify делает правильный JSON-ответ
    return jsonify([ad.to_dict() for ad in ads]), 200


# ---------------------------
# POST /ads -> создать объявление (только авторизованный)
# ---------------------------
@ads_bp.post("/ads")
@jwt_required()  # без токена сюда нельзя: будет 401 от Flask-JWT-Extended
def create_ad():
    """
    Защищённый эндпоинт:
    Создаёт объявление.

    Важно:
    - owner_id ставим по текущему пользователю из JWT,
      чтобы клиент НЕ мог создать объявление "от чужого имени".
    """
    # request.get_json(silent=True):
    # - пытается прочитать JSON тело запроса
    # - если JSON битый/не передан -> вернёт None, и ошибок парсинга не будет
    data = request.get_json(silent=True)

    # Проверяем, что пришёл JSON-объект, а не список/строка/None
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    # Берём поля из JSON.
    # data.get() безопаснее чем data["title"], потому что не бросает KeyError.
    title = data.get("title")
    description = data.get("description")

    # Валидация: title должен быть строкой и не быть пустым после strip()
    if not isinstance(title, str) or not title.strip():
        raise ApiError("Field 'title' is required", 400)

    # Валидация: description должен быть строкой и не быть пустым
    if not isinstance(description, str) or not description.strip():
        raise ApiError("Field 'description' is required", 400)

    # Получаем текущего пользователя из токена
    user = get_current_user()

    # Создаём объект объявления
    ad = Ad(
        title=title.strip(),                 # убираем лишние пробелы
        description=description.strip(),     # убираем лишние пробелы
        owner_id=user.id                     # владелец = текущий пользователь
    )

    # Добавляем в сессию ORM и сохраняем в БД
    db.session.add(ad)
    db.session.commit()

    # 201 Created — правильный код при создании ресурса
    return jsonify(ad.to_dict()), 201


# ---------------------------
# GET /ads/<id> -> получить объявление (публичный)
# ---------------------------
@ads_bp.get("/ads/<int:ad_id>")
def get_ad(ad_id: int):
    """
    Публичный эндпоинт:
    Возвращает одно объявление по его id.
    """
    ad = get_ad_or_404(ad_id)
    return jsonify(ad.to_dict()), 200


# ---------------------------
# DELETE /ads/<id> -> удалить объявление (только владелец)
# ---------------------------
@ads_bp.delete("/ads/<int:ad_id>")
@jwt_required()
def delete_ad(ad_id: int):
    """
    Защищённый эндпоинт:
    Удаляет объявление.

    Правило прав:
    - удалить может только владелец объявления
    """
    user = get_current_user()
    ad = get_ad_or_404(ad_id)

    # Проверяем право: owner_id объявления должен совпадать с id пользователя из JWT
    if ad.owner_id != user.id:
        # 403 Forbidden — "я тебя понял, но у тебя нет прав"
        raise ApiError("You are not the owner of this ad", 403)

    # Удаляем запись и сохраняем изменения
    db.session.delete(ad)
    db.session.commit()

    return jsonify({"status": "deleted", "id": ad_id}), 200


# ---------------------------
# PATCH /ads/<id> -> редактировать объявление (только владелец)
# ---------------------------
@ads_bp.patch("/ads/<int:ad_id>")
@jwt_required()
def update_ad(ad_id: int):
    """
    Защищённый эндпоинт:
    Частичное обновление объявления через PATCH.

    Правило прав:
    - редактировать может только владелец объявления

    Почему PATCH:
    - PATCH = частичное обновление (можно отправить только одно поле)
    - PUT   = полная замена объекта (обычно требуют все поля сразу)
    """
    user = get_current_user()
    ad = get_ad_or_404(ad_id)

    # Проверяем, что текущий пользователь владелец объявления
    if ad.owner_id != user.id:
        raise ApiError("You are not the owner of this ad", 403)

    # Читаем JSON, который содержит поля для обновления
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    # Разрешаем менять только определённые поля
    allowed = {"title", "description"}

    # Ищем "лишние" поля, которые менять нельзя
    # Например если клиент отправит: {"owner_id": 999} — мы это запретим
    unknown = set(data.keys()) - allowed
    if unknown:
        raise ApiError(f"Unknown fields: {sorted(list(unknown))}", 400)

    # Если пришёл title — валидируем и обновляем
    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            raise ApiError("Field 'title' must be a non-empty string", 400)
        ad.title = data["title"].strip()

    # Если пришёл description — валидируем и обновляем
    if "description" in data:
        if not isinstance(data["description"], str) or not data["description"].strip():
            raise ApiError("Field 'description' must be a non-empty string", 400)
        ad.description = data["description"].strip()

    # Сохраняем изменения в БД
    db.session.commit()

    # Возвращаем обновлённый объект
    return jsonify(ad.to_dict()), 200
