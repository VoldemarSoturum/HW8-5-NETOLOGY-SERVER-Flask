from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from .models import db, User
from .errors import ApiError

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    email = data.get("email")
    password = data.get("password")

    if not isinstance(email, str) or not email.strip():
        raise ApiError("Field 'email' is required", 400)
    if not isinstance(password, str) or len(password) < 6:
        raise ApiError("Field 'password' is required (min 6 chars)", 400)

    user = User(email=email.strip().lower())
    user.set_password(password)

    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("User with this email already exists", 409)

    return jsonify(user.to_dict()), 201


@auth_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Body must be JSON object", 400)

    email = data.get("email")
    password = data.get("password")

    if not isinstance(email, str) or not email.strip():
        raise ApiError("Field 'email' is required", 400)
    if not isinstance(password, str) or not password:
        raise ApiError("Field 'password' is required", 400)

    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user or not user.check_password(password):
        raise ApiError("Invalid email or password", 401)

    # ✅ FIX: identity должен быть строкой, иначе будет 422 "Subject must be a string"
    token = create_access_token(identity=str(user.id))

    return jsonify({"access_token": token}), 200
