from flask import g, Blueprint, flash, redirect, render_template, url_for, Response, request
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import abort

from typing import Union, Any, Optional
import json
from matplotlib.figure import Figure
from io import BytesIO
import base64
from decimal import Decimal

from .auth import login_required
from .db import db, get_nucleus_id, User, Nucleus, ReactionData, TargetMaterial
from .NucleusData import get_excitations
from .SPSReaction import Reaction, RxnParameters
from .SPSTarget import SPSTarget, TargetLayer
from .forms import PlotForm, ReactionForm, TargetForm

PLOT_EX: str = "E"
PLOT_KE: str = "K"
PLOT_Z: str = "Z"

bp = Blueprint("spsplot", __name__, url_prefix="/spsplot")

def generate_plot(beamEnergy: float, spsAngle: float, magneticField: float, rhoMin: float, rhoMax: float, plotType: str) -> str:

    data: User = db.session.execute(select(User).options(joinedload(User.reactions).subqueryload(ReactionData.target_material)).where(User.id == g.user.id)).scalar()

    rhos = []
    exs = []
    kes = []
    zs = []
    rxns = []
    fig = Figure(figsize=(16,9))
    axes = fig.subplots()
    for ir, rxn in enumerate(data.reactions):
        targetLayers = json.loads(rxn.target_material.compounds)
        targetThicks = json.loads(rxn.target_material.thicknesses)
        targetMat = SPSTarget([TargetLayer(layer, float(targetThicks[i])) for i, layer in enumerate(targetLayers) if len(layer) != 0])
        reaction = Reaction(
            RxnParameters(rxn.target_nuc_id, rxn.projectile_nuc_id, rxn.ejectile_nuc_id, rxn.residual_nuc_id, beamEnergy, magneticField, spsAngle), 
            targetMat
        )
        excitations = json.loads(rxn.excitations)
        for ex in excitations:
            ke = reaction.calculate_ejectile_KE(ex)
            rho = reaction.convert_ejectile_KE_2_rho(ke)
            z = reaction.calculate_focal_plane_offset(ke)
            exs.append(ex)
            rxns.append(ir+1)
            kes.append(ke)
            rhos.append(rho)
            zs.append(z)
    axes.plot(rhos, rxns, marker="o", linestyle="None")

    for i, y in enumerate(rxns):
        x = rhos[i]
        if plotType == PLOT_KE:
            axes.annotate(f"{kes[i]:.2f}", (x,y), textcoords="offset points", xytext=(0,10), ha="center", rotation="vertical")
        elif plotType == PLOT_Z:
            axes.annotate(f"{zs[i]:.2f}", (x,y), textcoords="offset points", xytext=(0,10), ha="center", rotation="vertical")
        else:
            axes.annotate(f"{exs[i]:.2f}", (x,y), textcoords="offset points", xytext=(0,10), ha="center", rotation="vertical")

    ylabels = [rxn.latex_rxn_symbol for rxn in data.reactions]
    ylabels.append("Reactions")
    axes.set_yticks(range(1,len(data.reactions)+2))
    axes.set_yticklabels(ylabels)
    axes.set_xlim(rhoMin, rhoMax)
    axes.set_xlabel(r"$\rho$ (cm)")
    fig.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="svg")
    data = base64.b64encode(buffer.getbuffer()).decode("utf-8")
    return data
    

@bp.route("/", methods=("GET", "POST"))
@login_required
def index() -> str:

    user: User = db.session.get(User, g.user.id)
    form = PlotForm()

    if form.validate_on_submit():
        return render_template("spsplot/index.html", reactions=user.reactions, target_mats=user.target_materials, form=form,
            plot = generate_plot(float(form.beam_energy.data), float(form.sps_angle.data), float(form.b_field.data), float(form.rho_min.data), float(form.rho_max.data), form.buttons.data)
        )
    return render_template("spsplot/index.html", reactions=user.reactions, target_mats=user.target_materials, form=form, plot=None)

@bp.route("/target/add", methods=("GET", "POST"))
@login_required
def add_target_material() -> Union[str, Response]:
    form = TargetForm()
    if form.validate_on_submit():
        layer_data: list[list[tuple[int, int]]] = [[], [], []] #list of all layers
        thicknesses: list[float] = [] #thickness of all layers
        symbols: list[str] = [] #layer symbols
        error = None

        for i, layer in enumerate(form.layers):
            if layer.thickness.data is not None:
                thicknesses.append(float(layer.thickness.data))
                symbol = ""
                for element in layer.elements:
                    if element.z.data is not None and element.a.data is not None and element.s.data is not None:
                        nuc_id = get_nucleus_id(element.z.data, element.a.data)
                        nuc: Nucleus = db.session.get(Nucleus, nuc_id)
                        symbol += f"{nuc.isotope}<sub>{element.s.data}</sub>"
                        layer_data[i].append((nuc_id, element.s.data))
                if symbol != "":
                    symbols.append(symbol)

        if len(thicknesses) == 0:
            error = "A target must have at least one layer"

        if error is not None:
            flash(error)
        else:
            db.session.add(TargetMaterial(user_id=g.user.id, mat_name=form.mat_name.data, mat_symbol=json.dumps(symbols), compounds=json.dumps(layer_data), thicknesses=json.dumps(thicknesses)))
            db.session.commit()
            return redirect(url_for("spsplot.index"))
    
    return render_template("spsplot/add_target.html", form=form)

def get_target_material(id: int, check_user: bool = True) -> TargetMaterial:

    mat: Optional[TargetMaterial] = db.session.get(TargetMaterial, id)

    if mat is None:
        abort(404, f"Requested target material {id} does not exist")
    if check_user and mat.user_id != g.user.id:
        abort(403)
    return mat

@bp.route("/target/<int:id>/update", methods=("GET", "POST"))
@login_required
def update_target_material(id: int) -> Union[str, Response]:
    mat = get_target_material(id)
    form = TargetForm()

    #Load up existing target data and put it in the form
    if request.method == "GET":
        form.mat_name.data = mat.mat_name
        load_thick = json.loads(mat.thicknesses)
        load_layers = json.loads(mat.compounds)
        for i, t in enumerate(load_thick):
            form.layers.entries[i].thickness.data = Decimal(t)
            for j, comp in enumerate(load_layers[i]):
                nuc: Nucleus = db.session.get(Nucleus, comp[0])
                form.layers.entries[i].elements[j].z.data = nuc.z
                form.layers.entries[i].elements[j].a.data = nuc.a
                form.layers.entries[i].elements[j].s.data = comp[1]

    if form.validate_on_submit():
        layer_data: list[list[tuple[int, int]]] = [[], [], []] #list of all layers
        thicknesses: list[float] = [] #thickness of all layers
        symbols: list[str] = [] #layer symbols
        error = None

        for i, layer in enumerate(form.layers):
            if layer.thickness.data is not None:
                thicknesses.append(float(layer.thickness.data))
                symbol = ""
                for element in layer.elements:
                    if element.z.data is not None and element.a.data is not None and element.s.data is not None:
                        nuc_id = get_nucleus_id(element.z.data, element.a.data)
                        nuc: Optional[Nucleus] = db.session.get(Nucleus, nuc_id)
                        if nuc is None:
                            error = f"Illegal nucleus Z={element.z.data} A={element.a.data}"
                        else:
                            symbol += f"{nuc.isotope}<sub>{element.s.data}</sub>"
                            layer_data[i].append((nuc_id, element.s.data))
                if symbol != "":
                    symbols.append(symbol)

        if len(thicknesses) == 0:
            error = "A target must have at least one layer"

        if error is not None:
            flash(error)
        else:
            mat.mat_name = form.mat_name.data
            mat.mat_symbol = json.dumps(symbols)
            mat.compounds = json.dumps(layer_data)
            mat.thicknesses = json.dumps(thicknesses)
            db.session.commit()
            return redirect(url_for("spsplot.index"))
    
    return render_template("spsplot/update_target.html", mat=mat, form=form)

@bp.route("/target/<int:id>/delete", methods=("GET", "POST"))
@login_required
def delete_target_material(id: int) -> Response:
    mat = get_target_material(id)
    db.session.delete(mat)
    db.session.commit()
    return redirect(url_for("spsplot.index"))

@bp.route("/rxn/add", methods=("GET", "POST"))
@login_required
def add_rxn() -> Union[str, Response]:
    form = ReactionForm()
    user: User = db.session.get(User, g.user.id)
    form.target_mat.choices = [(mat.id, mat.mat_name) for mat in user.target_materials]

    if form.validate_on_submit():
        error = None
        zr = form.zt.data + form.zp.data - form.ze.data
        ar = form.at.data + form.ap.data - form.ae.data
        if zr < 0 or ar < 1:
            error = f"Illegal reaction resulting in residual with Z:{zr} A:{ar}"
        else:
            targ_id = get_nucleus_id(form.zt.data, form.at.data)
            proj_id = get_nucleus_id(form.zp.data, form.ap.data)
            eject_id = get_nucleus_id(form.ze.data, form.ae.data)
            resid_id = get_nucleus_id(zr, ar)

            targ: Optional[Nucleus] = db.session.get(Nucleus, targ_id)
            proj: Optional[Nucleus] = db.session.get(Nucleus, proj_id)
            eject: Optional[Nucleus] = db.session.get(Nucleus, eject_id)
            resid: Optional[Nucleus] = db.session.get(Nucleus, resid_id)

            if targ is None or proj is None or eject is None or resid is None:
                error = f"One of the reactants is not a valid nucleus"

            if error is not None:
                flash(error)
            else:
                rxn_symbol = f"{targ.isotope}({proj.isotope},{eject.isotope}){resid.isotope}"
                latex_symbol = "$^{" + str(targ.a) + "}$" + targ.element + \
                               "($^{" + str(proj.a) + "}$" + proj.element + \
                               ",$^{" + str(eject.a) + "}$" + eject.element + \
                               ")$^{" + str(resid.a) + "}$" + resid.element
                excitations = json.dumps(get_excitations(resid_id))
                db.session.add(ReactionData(user_id=g.user.id, target_mat_id=form.target_mat.data, rxn_symbol=rxn_symbol, latex_rxn_symbol=latex_symbol,
                                            target_nuc_id=targ_id, projectile_nuc_id=proj_id, ejectile_nuc_id=eject_id, residual_nuc_id=resid_id, excitations=excitations))
                db.session.commit()
                return redirect(url_for("spsplot.index"))
    return render_template("spsplot/add_rxn.html", form=form)

def get_rxn(id: int, check_user: bool = True) -> ReactionData:

    rxn: Optional[ReactionData] = db.session.get(ReactionData, id)

    if rxn is None:
        abort(404, f"Requested reaction {id} does not exist")
    if check_user and rxn.user_id != g.user.id:
        abort(403)
    return rxn

@bp.route("/rxn/<int:id>/update", methods=("GET", "POST"))
@login_required
def update_rxn(id: int) -> Union[str, Response]:
    rxn = get_rxn(id)
    form = ReactionForm()
    user: User = db.session.get(User, g.user.id)
    form.target_mat.choices = [(mat.id, mat.mat_name) for mat in user.target_materials]

    if request.method == "GET":
        form.target_mat.data = rxn.target_mat_id
        form.zt.data = rxn.target_nucleus.z
        form.at.data = rxn.target_nucleus.a
        form.zp.data = rxn.projectile_nucleus.z
        form.ap.data = rxn.projectile_nucleus.a
        form.ze.data = rxn.ejectile_nucleus.z
        form.ae.data = rxn.ejectile_nucleus.a

    if form.validate_on_submit():
        error = None
        zr = form.zt.data + form.zp.data - form.ze.data
        ar = form.at.data + form.ap.data - form.ae.data
        if zr < 0 or ar < 1:
            error = f"Illegal reaction resulting in residual with Z:{zr} A:{ar}"
        else:
            targ_id = get_nucleus_id(form.zt.data, form.at.data)
            proj_id = get_nucleus_id(form.zp.data, form.ap.data)
            eject_id = get_nucleus_id(form.ze.data, form.ae.data)
            resid_id = get_nucleus_id(zr, ar)

            targ: Optional[Nucleus] = db.session.get(Nucleus, targ_id)
            proj: Optional[Nucleus] = db.session.get(Nucleus, proj_id)
            eject: Optional[Nucleus] = db.session.get(Nucleus, eject_id)
            resid: Optional[Nucleus] = db.session.get(Nucleus, resid_id)

            if targ is None or proj is None or eject is None or resid is None:
                error = f"One of the reactants is not a valid nucleus"

            if error is not None:
                flash(error)
            else:
                rxn.target_mat_id = form.target_mat.data
                rxn.rxn_symbol = f"{targ.isotope}({proj.isotope},{eject.isotope}){resid.isotope}"
                rxn.latex_rxn_symbol = "$^{" + str(targ.a) + "}$" + targ.element + \
                                       "($^{" + str(proj.a) + "}$" + proj.element + \
                                       ",$^{" + str(eject.a) + "}$" + eject.element + \
                                       ")$^{" + str(resid.a) + "}$" + resid.element
                rxn.target_nuc_id = targ_id
                rxn.projectile_nuc_id = proj_id
                rxn.ejectile_nuc_id = eject_id
                rxn.residual_nuc_id = resid_id
                rxn.excitations = json.dumps(get_excitations(resid_id))
                db.session.commit()
                return redirect(url_for("spsplot.index"))
    return render_template("spsplot/update_rxn.html", rxn=rxn, form=form)

@bp.route("/rxn/<int:id>/delete", methods=("GET", "POST"))
@login_required
def delete_rxn(id: int) -> Response:
    rxn = get_rxn(id)
    db.session.delete(rxn)
    db.session.commit()
    return redirect(url_for("spsplot.index"))
