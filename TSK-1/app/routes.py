from flask import Blueprint, request, jsonify
from .models import db, Ad
from .errors import ApiError

ads_bp = Blueprint("ads", __name__)


def validate_ad_payload(data: dict, required_fields: list[str]):
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    for field in required_fields:
        if field not in data:
            raise ApiError(f"Field '{field}' is required", 400)

        if not isinstance(data[field], str) or not data[field].strip():
            raise ApiError(f"Field '{field}' must be a non-empty string", 400)


def get_ad_or_404(ad_id: int) -> Ad:
    ad = Ad.query.get(ad_id)
    if ad is None:
        raise ApiError("Ad not found", 404)
    return ad


# -------------------------
# POST /ads -> создать
# GET  /ads -> получить список
# -------------------------
@ads_bp.route("/ads", methods=["POST", "GET"])
def ads_collection():
    if request.method == "POST":
        data = request.get_json(silent=True)
        validate_ad_payload(data, required_fields=["title", "description", "owner"])

        ad = Ad(
            title=data["title"].strip(),
            description=data["description"].strip(),
            owner=data["owner"].strip(),
        )
        db.session.add(ad)
        db.session.commit()

        return jsonify(ad.to_dict()), 201

    # GET /ads
    ads = Ad.query.order_by(Ad.created_at.desc()).all()
    return jsonify([ad.to_dict() for ad in ads]), 200


# -------------------------
# GET    /ads/<id> -> получить
# DELETE /ads/<id> -> удалить
# PATCH  /ads/<id> -> редактировать
# -------------------------
@ads_bp.route("/ads/<int:ad_id>", methods=["GET", "DELETE", "PATCH"])
def ad_item(ad_id: int):
    ad = get_ad_or_404(ad_id)

    if request.method == "GET":
        return jsonify(ad.to_dict()), 200

    if request.method == "DELETE":
        db.session.delete(ad)
        db.session.commit()
        return jsonify({"status": "deleted", "id": ad_id}), 200

    # PATCH
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    allowed_fields = {"title", "description", "owner"}
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

    if "owner" in data:
        if not isinstance(data["owner"], str) or not data["owner"].strip():
            raise ApiError("Field 'owner' must be a non-empty string", 400)
        ad.owner = data["owner"].strip()

    db.session.commit()
    return jsonify(ad.to_dict()), 200
