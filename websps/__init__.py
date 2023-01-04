import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from typing import Mapping, Any, Optional
from . import db
from . import auth
from . import home
from . import spsplot
from pathlib import Path

def create_app(test_config: Optional[Mapping[str, Any]]=None) -> Flask:
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI=f"sqlite+pysqlite:///{Path(app.instance_path) / 'websps.sqlite'}",
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # initialize database with app
    db.init_app(app)
    db.db.init_app(app)

    app.register_blueprint(home.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(spsplot.bp)

    return app
