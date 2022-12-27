import sqlite3
import click
from flask import current_app, g, Flask
import numpy as np

U2MEV: float = 931.4940954
ELECTRON_MASS: float = 0.000548579909

def get_nucleus_id(z: np.uint32, a: np.uint32) -> np.uint32:
    return z*z + z + a if z > a else a*a + z

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db() -> None:
    db = get_db()
    with current_app.open_resource("schema.sql") as file:
        db.executescript(file.read().decode("utf8"))
        with current_app.open_resource("data/mass.txt") as massfile:
            massfile.readline()
            massfile.readline()
            for line in massfile:
                entries = line.split()
                z = int(entries[1])
                a = int(entries[2])
                mass = (float(entries[4])  + 1.0e-6 * float(entries[5]) - float(z) * ELECTRON_MASS) * U2MEV
                elementSymbol = entries[3].decode("utf-8")
                isotopicSymbol = f"<sup>{a}</sup>{elementSymbol}"
                db.execute(
                    "INSERT INTO nucleus (id, z, a, mass, element, isotope) VALUES (?, ?, ?, ?, ?, ?)",
                    (get_nucleus_id(z, a), z, a, mass, elementSymbol, isotopicSymbol)
                )
                db.commit()

@click.command("init-db")
def init_db_command() -> None:
    #Initialize the database for the application, creating new tables (and clearing any existing)
    click.echo("Setting up the database...")
    init_db()
    click.echo("Done.")

def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)