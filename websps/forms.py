from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DecimalField, IntegerField, SelectField, RadioField, FormField, FieldList
from wtforms.validators import InputRequired, Optional, Length, ValidationError
from flask import Markup

def bot_field_validator(form, field):
    if len(field.data) != 0:
        raise ValidationError("You're a bot!")

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(1, 50)])
    password = PasswordField("Password", validators=[InputRequired(), Length(8, 50)])
    bot_type1_field = StringField("Password", validators=[bot_field_validator]) #Make this field hidden
    bot_type2_field = StringField("Test", validators=[bot_field_validator],default="Remove me!") #Users must remove this text

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

class LevelForm(FlaskForm):
    rxn_id = SelectField("Reaction", coerce=int, validators=[InputRequired()])
    excitation = DecimalField("Excitation", validators=[InputRequired()])