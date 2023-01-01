from flask import g, Blueprint, flash, redirect, render_template, request, url_for, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload, subqueryload
from werkzeug.exceptions import abort
from .auth import login_required
from .db import db, get_nucleus_id, User, Nucleus, ReactionData, TargetMaterial
from .NucleusData import get_excitations
from .SPSReaction import Reaction, RxnParameters
from .SPSTarget import SPSTarget, TargetLayer
from typing import Union, Any, Optional
import json
from matplotlib.figure import Figure
from io import BytesIO
import base64

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

    if request.method == "POST":
        beamEnergy = float(request.form["beamEnergy"])
        spsAngle = float(request.form["spsAngle"])
        magneticField = float(request.form["bfield"])
        rhoMin = float(request.form["rhoMin"])
        rhoMax = float(request.form["rhoMax"])
        plotType = request.form["plotType"]
        plot = generate_plot(beamEnergy, spsAngle, magneticField, rhoMin, rhoMax, plotType)
        return render_template("spsplot/index.html", reactions=user.reactions, target_mats=user.target_materials, plot=plot)
    return render_template("spsplot/index.html", reactions=user.reactions, target_mats=user.target_materials, plot=None)

@bp.route("/target/add", methods=("GET", "POST"))
@login_required
def add_target_material() -> Union[str, Response]:
    if request.method == "POST":
        layer_data: list[list[tuple[int, int]]] = [[], [], []] #list of all layers
        thicknesses: list[float] = [] #thickness of all layers
        symbols: list[str] = [] #layer symbols
        mat_name = request.form["mat_name"]
        error = None
        #Retrive data from all layers
        for i in range(1, 4):
            thick_str = request.form[f"layer{i}_thickness"]
            if thick_str != "":
                thicknesses.append(float(thick_str))
                symbol = ""
                for j in range(1, 4):
                    z = request.form[f"layer{i}_z{j}"]
                    a = request.form[f"layer{i}_a{j}"]
                    s = request.form[f"layer{i}_s{j}"]
                    if z != "" and a != "" and s != "":
                        nucleus: Nucleus  = db.session.get(Nucleus, get_nucleus_id(int(z), int(a)))
                        symbol += f"{nucleus.isotope}<sub>{s}</sub>"
                        layer_data[i-1].append((get_nucleus_id(int(z), int(a)), int(s)))
                if symbol != "":
                    symbols.append(symbol)

        if mat_name is None:
            error = "Target material must have a name"

        if error is not None:
            flash(error)
        else:
            db.session.add(TargetMaterial(user_id=g.user.id, mat_name=mat_name, mat_symbol=json.dumps(symbols), compounds=json.dumps(layer_data), thicknesses=json.dumps(thicknesses)))
            db.session.commit()
            return redirect(url_for("spsplot.index"))
    
    return render_template("spsplot/add_target.html")

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
    mat: Optional[TargetMaterial] = db.session.get(TargetMaterial, id)
    if request.method == "POST":
        layer_data: list[list[tuple[int, int]]] = [[], [], []] #list of all layers
        thicknesses: list[float] = [] #thickness of all layers
        symbols: list[str] = [] #layer symbols
        mat_name = request.form["mat_name"]
        error = None
        #Retrive data from all layers
        for i in range(1, 4):
            thick_str = request.form[f"layer{i}_thickness"]
            if thick_str != "":
                thicknesses.append(float(thick_str))
                symbol = ""
                for j in range(1, 4):
                    z = request.form[f"layer{i}_z{j}"]
                    a = request.form[f"layer{i}_a{j}"]
                    s = request.form[f"layer{i}_s{j}"]
                    if z != "" and a != "" and s != "":
                        nucleus: Nucleus  = db.session.get(Nucleus, get_nucleus_id(int(z), int(a)))
                        symbol += f"{nucleus['isotope']}<sub>{s}</sub>"
                        layer_data[i].append((get_nucleus_id(int(z), int(a)), s))
                if symbol != "":
                    symbols.append(symbol)

        if mat_name is None:
            error = "Target material must have a name"
        if mat is None:
            error = "Illegal target material attempted to be modified"

        if error is not None:
            flash(error)
        else:
            mat.mat_name = mat_name
            mat.mat_symbol = json.dumps(symbols)
            mat.compounds = json.dumps(layer_data)
            mat.thicknesses = json.dumps(thicknesses)
            db.session.commit()
            return redirect(url_for("spsplot.index"))
    
    return render_template("spsplot/update_target.html", mat=mat)

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
    if request.method == "POST":
        mat_id = request.form["mat_id"]
        zt = int(request.form["zt"])
        at = int(request.form["at"])
        zp = int(request.form["zp"])
        ap = int(request.form["ap"])
        ze = int(request.form["ze"])
        ae = int(request.form["ae"])
        error = None

        zr = zt + zp - ze
        ar = at + ap - ae
        if zr < 0 or ar < 1:
            error = f"Illegal residual nucleus with Z:{zr} A:{ar}"
        else:
            targID = get_nucleus_id(zt, at)
            projID = get_nucleus_id(zp, ap)
            ejectID = get_nucleus_id(ze, ae)
            residID = get_nucleus_id(zr, ar)

            targ: Optional[Nucleus] = db.session.get(Nucleus, targID)
            proj: Optional[Nucleus] = db.session.get(Nucleus, projID)
            eject: Optional[Nucleus] = db.session.get(Nucleus, ejectID)
            resid: Optional[Nucleus] = db.session.get(Nucleus, residID)

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
                excitations = json.dumps(get_excitations(residID))
                db.session.add(ReactionData(user_id=g.user.id, target_mat_id=mat_id, rxn_symbol=rxn_symbol, latex_rxn_symbol=latex_symbol,
                                            target_nuc_id=targID, projectile_nuc_id=projID, ejectile_nuc_id=ejectID, residual_nuc_id=residID, excitations=excitations))
                db.session.commit()
                return redirect(url_for("spsplot.index"))
    
    user: User = db.session.get(User, g.user.id)

    return render_template("spsplot/add_rxn.html", target_mats=user.target_materials)

def get_rxn(id: int, check_user: bool = True) -> ReactionData:

    rxn: Optional[ReactionData] = db.session.get(ReactionData, id)

    if rxn is None:
        abort(404, f"Requested reaction {id} does not exist")
    if check_user and rxn.user_id != g.user.id:
        abort(403)
    return rxn

@bp.route("/rxn/<int:id>/update", methods=("GET", "POST"))
@login_required
def update_rxn(id: int) -> str:
    rxn = get_rxn(id)
    return render_template("spsplot/update_rxn.html", rxn=rxn)

@bp.route("/rxn/<int:id>/delete", methods=("GET", "POST"))
@login_required
def delete_rxn(id: int) -> Response:
    rxn = get_rxn(id)
    db.session.delete(rxn)
    db.session.commit()
    return redirect(url_for("spsplot.index"))
