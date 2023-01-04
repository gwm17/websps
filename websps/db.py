import click
from flask import current_app, Flask
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash
from datetime import datetime

U2MEV: float = 931.4940954
ELECTRON_MASS: float = 0.000548579909

db = SQLAlchemy()

class Nucleus(db.Model):
    __tablename__ = "nucleus"
    id: int = Column(Integer, primary_key=True)
    z: int = Column(Integer, nullable=False)
    a: int = Column(Integer, nullable=False)
    mass: float = Column(Float, nullable=False)
    element: str = Column(String, nullable=False)
    isotope: str = Column(String, nullable=False)

class TargetMaterial(db.Model):
    __tablename__ = "target_material"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: int = Column(Integer, ForeignKey("user.id"))
    mat_name: str = Column(String, nullable=False)
    mat_symbol: str = Column(String, nullable=False)
    compounds: str = Column(String, nullable=False)
    thicknesses: str = Column(String, nullable=False)
    reactions = relationship("ReactionData", back_populates="target_material", cascade="save-update, merge, delete")

class Level(db.Model):
    __tablename__ = "level"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: int = Column(Integer, ForeignKey("user.id"))
    reaction_id: int = Column(Integer, ForeignKey("reaction.id"))
    excitation: float = Column(Float)

    reaction = relationship("ReactionData", back_populates="user_levels")

class ReactionData(db.Model):
    __tablename__ = "reaction"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: int = Column(Integer, ForeignKey("user.id"))
    target_mat_id: int = Column(Integer, ForeignKey("target_material.id"))
    rxn_symbol: str = Column(String, nullable=False)
    latex_rxn_symbol: str = Column(String, nullable=False)
    target_nuc_id: int = Column(Integer, ForeignKey("nucleus.id"))
    projectile_nuc_id: int = Column(Integer, ForeignKey("nucleus.id"))
    ejectile_nuc_id: int = Column(Integer, ForeignKey("nucleus.id"))
    residual_nuc_id: int = Column(Integer, ForeignKey("nucleus.id"))
    nndc_levels: str = Column(String)

    target_material: TargetMaterial = relationship("TargetMaterial", back_populates="reactions")
    target_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[target_nuc_id])
    projectile_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[projectile_nuc_id])
    ejectile_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[ejectile_nuc_id])
    residual_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[residual_nuc_id])
    user_levels: list[Level] = relationship("Level", back_populates="reaction", cascade="save-update, merge, delete")

class User(db.Model):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    date_created = Column(DateTime, nullable=False)
    date_last_login = Column(DateTime, nullable=False)

    target_materials: list[TargetMaterial] = relationship("TargetMaterial")
    reactions: list[ReactionData] = relationship("ReactionData")
    levels: list[Level] = relationship("Level")

def get_nucleus_id(z: np.uint32, a: np.uint32) -> np.uint32:
    return z*z + z + a if z > a else a*a + z

def init_db() -> None:
    db.drop_all()
    db.create_all()
    admin = User(username=current_app.config.get("ADMIN_USERNAME"), password=generate_password_hash(current_app.config.get("ADMIN_PASSWORD")), date_created=datetime.now(), date_last_login=datetime.now())
    db.session.add(admin)
    db.session.commit()
    with current_app.open_resource("data/mass.txt") as massfile:
        massfile.readline()
        massfile.readline()
        for line in massfile:
            nuc = Nucleus()
            entries = line.split()
            nuc.z = int(entries[1])
            nuc.a = int(entries[2])
            nuc.id = get_nucleus_id(nuc.z, nuc.a)
            nuc.mass = (float(entries[4])  + 1.0e-6 * float(entries[5]) - float(nuc.z) * ELECTRON_MASS) * U2MEV
            nuc.element = entries[3].decode("utf-8")
            nuc.isotope = f"<sup>{nuc.a}</sup>{nuc.element}"
            db.session.add(nuc)
            db.session.commit()

@click.command("init-db")
def init_db_command() -> None:
    #Initialize the database for the application, creating new tables (and clearing any existing)
    click.echo("Setting up the database...")
    init_db()
    click.echo("Done.")

def init_app(app: Flask) -> None:
    app.cli.add_command(init_db_command)