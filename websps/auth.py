import functools
from flask import g, Blueprint, flash, redirect, render_template, request, session, url_for, Response, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import Optional, Union, Callable

from .db import db, User
from .forms import LoginForm


bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/register", methods=("GET", "POST"))
def register() -> Union[str, Response]:

    form = LoginForm()
    error = None
    if form.validate_on_submit():
        user = User(username=form.username.data, password=generate_password_hash(form.password.data))
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            error = f"Username {user.username} already exists"
            flash(error)
            db.session.rollback()
        else:
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)

@bp.route("/login", methods=("GET", "POST"))
def login() -> Union[str, Response]:
    form = LoginForm()
    if form.validate_on_submit():
        user: Optional[User] = db.session.execute(select(User).filter_by(username=form.username.data)).scalar_one_or_none()
        error = None
        if user is None:
            error = "Incorrect username"
        elif not check_password_hash(user.password, form.password.data):
            error = "Incorrect password"
        
        if error is None:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("home.index"))
        
        flash(error)
    return render_template("auth/login.html", form=form)

#Load user data based on login to g
@bp.before_app_request
def load_logged_in_user() -> None:
    userID = session.get("user_id")
    if userID is None:
        g.user = None
    else:
        g.user = db.session.get(User, userID)

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

def is_current_user_is_admin() -> bool:
    if g.user is not None and g.user.username == current_app.config.get("ADMIN_USERNAME"):
        return True
    else:
        return False

#function decorator which enforces admin login
def admin_required(view: Callable):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user.username != current_app.config.get("ADMIN_USERNAME"):
            flash("In order to access this information you must be logged in as admin!")
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped_view
