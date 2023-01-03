import functools
from flask import g, Blueprint, flash, redirect, render_template, request, session, url_for, Response
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

    # if request.method == "POST":
    #     user = User(
    #         username = request.form["username"],
    #         password = request.form["password"]
    #     )
    #     error: Optional[str] = None

    #     if not user.username:
    #         error = "Username is required"
    #     elif not user.password:
    #         error = "Password is required"

    #     if error is None:
    #         try:
    #             db.session.add(user)
    #             db.session.commit()
    #         except IntegrityError:
    #             error = f"Username {user.username} already exists"
    #             db.session.rollback()
    #         else:
    #             return redirect(url_for("auth.login"))

    #     flash(error)

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
    # if request.method == "POST":
    #     username = request.form["username"]
    #     password = request.form["password"]
    #     error: Optional[str] = None

    #     user: User = db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()

    #     if user is None:
    #         error = "Incorrect username"
    #     elif not check_password_hash(user.password, password):
    #         error = "Incorrect password"
        
    #     if error is None:
    #         session.clear()
    #         session["user_id"] = user.id
    #         return redirect(url_for("home.index"))

    #     flash(error)

    # return render_template("auth/login.html")

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
