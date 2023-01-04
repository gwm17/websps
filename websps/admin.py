from flask import Blueprint, redirect, render_template, url_for, Response
from werkzeug.exceptions import abort
from sqlalchemy import select, delete

from .auth import admin_required
from .db import db, User, ReactionData, TargetMaterial, Level

from typing import Optional

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("/", methods=("GET", "POST"))
@admin_required
def index() -> str:
    users = db.session.execute(select(User)).scalars()
    return render_template("admin/index.html", users=users)

def get_user(id: int) -> User:
    user: Optional[User] = db.session.get(User, id)

    if user is None:
        abort(404, f"Requested user {id} does not exist")
    return user

@bp.route("/user/<int:id>/inspect", methods=("GET", "POST"))
@admin_required
def inspect_user(id: int) -> str:
    user = get_user(id)
    return render_template("admin/inspect_user.html", user=user)

@bp.route("/user/<int:id>/clear", methods=("GET", "POST"))
@admin_required
def clear_user_data(id: int) -> Response:
    user = get_user(id)
    db.session.execute(delete(TargetMaterial).where(TargetMaterial.user_id == id))
    db.session.execute(delete(ReactionData).where(ReactionData.user_id == id))
    db.session.execute(delete(Level).where(Level.user_id == id))
    db.session.commit()
    return redirect(url_for("admin.index"))

@bp.route("/user/<int:id>/delete", methods=("GET", "POST"))
@admin_required
def delete_user(id: int) -> Response:
    user = get_user(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("admin.index"))
