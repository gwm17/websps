from flask import Blueprint, render_template, redirect, url_for, Response
from .auth import is_current_user_is_admin

from typing import Union

bp = Blueprint("home", __name__)

@bp.route("/")
def index() -> Union[str, Response]:
    if is_current_user_is_admin():
        return redirect(url_for("admin.index"))

    return render_template("home/index.html")

@bp.route("/about")
def about() -> str:
    return render_template("home/about.html")