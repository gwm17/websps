import functools
from flask import g, Blueprint, flash, redirect, render_template, request, session, url_for, Response
from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_db
from typing import Optional, Union, Callable

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/register", methods=("GET", "POST"))
def register() -> Union[str, Response]:
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        error: Optional[str] = None

        if not username:
            error = "Username is required"
        elif not password:
            error = "Password is required"

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                db.commit()
            except db.IntegrityError:
                error = f"Username {username} already exists"
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")

@bp.route("/login", methods=("GET", "POST"))
def login() -> Union[str, Response]:
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        error: Optional[str] = None

        user = db.execute(
            "SELECT * FROM user WHERE username=?",
            (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username"
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password"
        
        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("home.index"))

        flash(error)

    return render_template("auth/login.html")

#Load user data based on login to g
@bp.before_app_request
def load_logged_in_user() -> None:
    userID = session.get("user_id")
    if userID is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT * FROM user WHERE id=?",
            (userID,)
        ).fetchone()

@bp.route("/logout")
def logout() -> Response:
    session.clear()
    return redirect(url_for("home.index"))

#function decorator which checks for login
def login_required(view: Callable):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)
    
    return wrapped_view
