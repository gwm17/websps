import sqlite3
import click
from flask import current_app, g, Flask
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, Float, Time, ForeignKey
from sqlalchemy.orm import relationship
from pathlib import Path
from typing import Optional

U2MEV: float = 931.4940954
ELECTRON_MASS: float = 0.000548579909
DATABASE_NAME = "sqlite+pysqlite:///" + str(Path(__file__) / ".." / "instance" / "websps.sqlite")

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
    reactions = relationship("ReactionData", back_populates="target_material", cascade="delete")

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
    excitations: str = Column(String)

    target_material: TargetMaterial = relationship("TargetMaterial", back_populates="reactions")
    target_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[target_nuc_id])
    projectile_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[projectile_nuc_id])
    ejectile_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[ejectile_nuc_id])
    residual_nucleus: Nucleus = relationship("Nucleus", foreign_keys=[residual_nuc_id])

class User(db.Model):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)

    target_materials: list[TargetMaterial] = relationship("TargetMaterial")
    reactions: list[ReactionData] = relationship("ReactionData")

def get_nucleus_id(z: np.uint32, a: np.uint32) -> np.uint32:
    return z*z + z + a if z > a else a*a + z

def init_db() -> None:
    db.drop_all()
    db.create_all()
    with current_app.open_resource("data/mass.txt") as massfile:
        massfile.readline()
        massfile.readline()
        for line in massfile:
            nuc = Nucleus()
            entries = line.split()
            nuc.z = int(entries[1])
            nuc.a = int(entries[2])
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