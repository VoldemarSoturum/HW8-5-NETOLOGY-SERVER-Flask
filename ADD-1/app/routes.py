from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from .models import db, Ad
from .errors import ApiError

ads_bp = Blueprint("ads", __name__)


def validate_ad_payload(data: dict, required_fields: list[str]):
    """Проверка входного JSON на обязательные поля"""
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    for field in required_fields:
        if field not in data:
            raise ApiError(f"Field '{field}' is required", 400)

        if not isinstance(data[field], str) or not data[field].strip():
            raise ApiError(f"Field '{field}' must be a non-empty string", 400)


def get_ad_or_404(ad_id: int) -> Ad:
    """Получить объявление или вернуть 404"""
    ad = Ad.query.get(ad_id)
    if ad is None:
        raise ApiError("Ad not found", 404)
    return ad


def check_owner(ad: Ad):
    """Проверяем, что текущий пользователь — владелец объявления"""
    user_id = int(get_jwt_identity())  # JWT identity у нас строка -> приводим к int
    if ad.owner_id != user_id:
        raise ApiError("You are not the owner of this ad", 403)


# -------------------------
# GET /ads -> список (публично)
# -------------------------
@ads_bp.get("/ads")
def get_ads():
    ads = Ad.query.order_by(Ad.created_at.desc()).all()
    return jsonify([ad.to_dict() for ad in ads]), 200


# -------------------------
# POST /ads -> создать (ТОЛЬКО авторизованный)
# -------------------------
@ads_bp.post("/ads")
@jwt_required()
def create_ad():
    data = request.get_json(silent=True)
    validate_ad_payload(data, required_fields=["title", "description"])

    user_id = int(get_jwt_identity())

    ad = Ad(
        title=data["title"].strip(),
        description=data["description"].strip(),
        owner_id=user_id,  # ✅ владелец берётся из JWT
    )

    db.session.add(ad)
    db.session.commit()

    return jsonify(ad.to_dict()), 201


# -------------------------
# GET /ads/<id> -> получить (публично)
# -------------------------
@ads_bp.get("/ads/<int:ad_id>")
def get_ad(ad_id: int):
    ad = get_ad_or_404(ad_id)
    return jsonify(ad.to_dict()), 200


# -------------------------
# PATCH /ads/<id> -> редактировать (ТОЛЬКО владелец)
# -------------------------
@ads_bp.patch("/ads/<int:ad_id>")
@jwt_required()
def update_ad(ad_id: int):
    ad = get_ad_or_404(ad_id)
    check_owner(ad)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    allowed_fields = {"title", "description"}
    unknown_fields = set(data.keys()) - allowed_fields
    if unknown_fields:
        raise ApiError(f"Unknown fields: {sorted(list(unknown_fields))}", 400)

    if "title" in data:
        if not isinstance(data["title"], str) or not data["title"].strip():
            raise ApiError("Field 'title' must be a non-empty string", 400)
        ad.title = data["title"].strip()

    if "description" in data:
        if not isinstance(data["description"], str) or not data["description"].strip():
            raise ApiError("Field 'description' must be a non-empty string", 400)
        ad.description = data["description"].strip()

    db.session.commit()
    return jsonify(ad.to_dict()), 200


# -------------------------
# DELETE /ads/<id> -> удалить (ТОЛЬКО владелец)
# -------------------------
@ads_bp.delete("/ads/<int:ad_id>")
@jwt_required()
def delete_ad(ad_id: int):
    ad = get_ad_or_404(ad_id)
    check_owner(ad)

    db.session.delete(ad)
    db.session.commit()

    return jsonify({"status": "deleted", "id": ad_id}), 200
