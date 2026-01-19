from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from .models import db, Ad, User
from .errors import ApiError

ads_bp = Blueprint("ads", __name__)


def get_current_user() -> User:
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user is None:
        raise ApiError("User not found", 401)
    return user


def get_ad_or_404(ad_id: int) -> Ad:
    ad = Ad.query.get(ad_id)
    if ad is None:
        raise ApiError("Ad not found", 404)
    return ad


# ✅ GET /ads -> список (публичный)
@ads_bp.get("/ads")
def get_ads():
    ads = Ad.query.order_by(Ad.created_at.desc()).all()
    return jsonify([ad.to_dict() for ad in ads]), 200


# ✅ POST /ads -> создать (может только авторизованный!)
@ads_bp.post("/ads")
@jwt_required()
def create_ad():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    title = data.get("title")
    description = data.get("description")

    if not isinstance(title, str) or not title.strip():
        raise ApiError("Field 'title' is required", 400)
    if not isinstance(description, str) or not description.strip():
        raise ApiError("Field 'description' is required", 400)

    user = get_current_user()

    ad = Ad(
        title=title.strip(),
        description=description.strip(),
        owner_id=user.id
    )

    db.session.add(ad)
    db.session.commit()

    return jsonify(ad.to_dict()), 201


# ✅ GET /ads/<id> -> получить (публичный)
@ads_bp.get("/ads/<int:ad_id>")
def get_ad(ad_id: int):
    ad = get_ad_or_404(ad_id)
    return jsonify(ad.to_dict()), 200


# ✅ DELETE /ads/<id> -> удалить (может только владелец сообщения)
@ads_bp.delete("/ads/<int:ad_id>")
@jwt_required()
def delete_ad(ad_id: int):
    user = get_current_user()
    ad = get_ad_or_404(ad_id)

    if ad.owner_id != user.id:
        raise ApiError("You are not the owner of this ad", 403)

    db.session.delete(ad)
    db.session.commit()

    return jsonify({"status": "deleted", "id": ad_id}), 200


# ✅ PATCH /ads/<id> -> редактировать (только владелец)
@ads_bp.patch("/ads/<int:ad_id>")
@jwt_required()
def update_ad(ad_id: int):
    user = get_current_user()
    ad = get_ad_or_404(ad_id)

    if ad.owner_id != user.id:
        raise ApiError("You are not the owner of this ad", 403)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    allowed = {"title", "description"}
    unknown = set(data.keys()) - allowed
    if unknown:
        raise ApiError(f"Unknown fields: {sorted(list(unknown))}", 400)

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
