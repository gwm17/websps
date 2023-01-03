from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SelectField, RadioField, FormField, FieldList
from wtforms.validators import InputRequired, Optional
from flask import Markup

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = StringField("Password", validators=[InputRequired()])

class TargetElementForm(FlaskForm):
    z = IntegerField("Z", validators=[Optional()])
    a = IntegerField("A", validators=[Optional()])
    s = IntegerField("S", validators=[Optional()])

class TargetLayerForm(FlaskForm):
    thickness = DecimalField(Markup("Thickness &mu;g/cm<sup>2</sup>"), validators=[Optional()])
    elements = FieldList(FormField(TargetElementForm), min_entries=3, max_entries=3)

class TargetForm(FlaskForm):
    mat_name = StringField("Target Name", validators=[InputRequired()])
    layers = FieldList(FormField(TargetLayerForm), min_entries=3, max_entries=3)

class ReactionForm(FlaskForm):
    target_mat = SelectField("Target Material", coerce=int, validators=[InputRequired()])
    zt = IntegerField("ZT", validators=[InputRequired()])
    at = IntegerField("AT", validators=[InputRequired()])
    zp = IntegerField("ZP", validators=[InputRequired()])
    ap = IntegerField("AP", validators=[InputRequired()])
    ze = IntegerField("ZE", validators=[InputRequired()])
    ae = IntegerField("AE", validators=[InputRequired()])

class PlotForm(FlaskForm):
    beam_energy = DecimalField("Beam Energy (MeV)", validators=[InputRequired()])
    sps_angle = DecimalField("SPS Angle (deg)", validators=[InputRequired()])
    b_field = DecimalField("B-Field (kG)", validators=[InputRequired()])
    rho_min = DecimalField(Markup("&rho; Min (cm)"), validators=[InputRequired()])
    rho_max = DecimalField(Markup("&rho; Max (cm)"), validators=[InputRequired()])
    buttons = RadioField(choices=[("E", "Show Excitation (MeV)"), ("K", "Show Ejectile KE (MeV)"), ("Z", "Show Z-Offset (cm)")], validators=[InputRequired()])