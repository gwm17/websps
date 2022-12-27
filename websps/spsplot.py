from flask import g, Blueprint, flash, redirect, render_template, request, url_for, Response
from werkzeug.exceptions import abort
from .auth import login_required
from .db import get_db, get_nucleus_id
from .NucleusData import get_excitations
from .SPSReaction import Reaction, RxnParameters
from .SPSTarget import SPSTarget, TargetLayer
from typing import Union, Any
import json
from matplotlib.figure import Figure
from io import BytesIO
import base64

PLOT_EX: str = "E"
PLOT_KE: str = "K"
PLOT_Z: str = "Z"

bp = Blueprint("spsplot", __name__, url_prefix="/spsplot")

def generate_plot(beamEnergy: float, spsAngle: float, magneticField: float, rhoMin: float, rhoMax: float, plotType: str) -> str:
    db = get_db()
    data = db.execute(
        "SELECT r.latex_rxn_symbol, r.target_nuc_id, r.projectile_nuc_id, r.ejectile_nuc_id, r.residual_nuc_id, r.excitations, t.compounds, t.thicknesses"
        " FROM reaction r JOIN target_material t ON r.target_mat_id = t.id WHERE r.user_id=?",
        (g.user['id'],)
    ).fetchall()

    rhos = []
    exs = []
    kes = []
    zs = []
    rxns = []
    fig = Figure()
    axes = fig.subplots()
    for ir, rxn in enumerate(data):
        targetLayers = json.loads(rxn["compounds"])
        targetThicks = json.loads(rxn["thicknesses"])
        targetMat = SPSTarget([TargetLayer(layer, float(targetThicks[i])) for i, layer in enumerate(targetLayers) if len(layer) != 0])
        reaction = Reaction(
            RxnParameters(rxn["target_nuc_id"], rxn["projectile_nuc_id"], rxn["ejectile_nuc_id"], rxn["residual_nuc_id"], beamEnergy, magneticField, spsAngle), 
            targetMat
        )
        excitations = json.loads(rxn["excitations"])
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

    ylabels = [rxn['latex_rxn_symbol'] for rxn in data]
    ylabels.append("Reactions")
    axes.set_yticks(range(1,len(data)+2))
    axes.set_yticklabels(ylabels)
    axes.set_xlim(rhoMin, rhoMax)
    axes.set_xlabel(r"$\rho$ (cm)")
    fig.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    data = base64.b64encode(buffer.getbuffer()).decode("ascii")
    return data
    

@bp.route("/", methods=("GET", "POST"))
@login_required
def index() -> str:
    db = get_db()
    target_mats = db.execute(
        "SELECT id, mat_name, mat_symbol, thicknesses FROM target_material t WHERE t.user_id = ?",
        (g.user["id"],)
    ).fetchall()
    reactions = db.execute(
        "SELECT r.id, r.rxn_symbol, t.mat_name FROM reaction r JOIN target_material t ON r.target_mat_id = t.id WHERE r.user_id = ?",
        (g.user["id"],)
    ).fetchall()

    if request.method == "POST":
        beamEnergy = float(request.form["beamEnergy"])
        spsAngle = float(request.form["spsAngle"])
        magneticField = float(request.form["bfield"])
        rhoMin = float(request.form["rhoMin"])
        rhoMax = float(request.form["rhoMax"])
        plotType = request.form["plotType"]
        plot = generate_plot(beamEnergy, spsAngle, magneticField, rhoMin, rhoMax, plotType)
        return render_template("spsplot/index.html", reactions=reactions, target_mats=target_mats, plot=plot)
    return render_template("spsplot/index.html", reactions=reactions, target_mats=target_mats, plot=None)

@bp.route("/target/add", methods=("GET", "POST"))
@login_required
def add_target_material() -> Union[str, Response]:
    if request.method == "POST":
        layer_data: list[list[tuple[int, int]]] = [[], [], []] #list of all layers
        thicknesses: list[float] = [0., 0., 0.] #thickness of all layers
        symbols: list[str] = [] #layer symbols
        mat_name = request.form["mat_name"]
        error = None
        #Retrive data from all layers
        db = get_db()
        for i in range(1, 4):
            thicknesses[i-1] = 0.0 if request.form[f"layer{i}_thickness"] == "" else (float(request.form[f"layer{i}_thickness"]))
            symbol = ""
            for j in range(1, 4):
                z = request.form[f"layer{i}_z{j}"]
                a = request.form[f"layer{i}_a{j}"]
                s = request.form[f"layer{i}_s{j}"]
                if z != "" and a != "" and s != "":
                    nucleus  = db.execute("SELECT id, element, isotope FROM nucleus n WHERE n.id = ?", (get_nucleus_id(int(z), int(a)),)).fetchone()
                    symbol += f"{nucleus['isotope']}<sub>{s}</sub>"
                    layer_data[i-1].append((get_nucleus_id(int(z), int(a)), int(s)))
            if symbol != "":
                symbols.append(symbol)

        if mat_name is None:
            error = "Target material must have a name"

        if error is not None:
            flash(error)
        else:
            db.execute(
                "INSERT INTO target_material (user_id, mat_name, mat_symbol, compounds, thicknesses) VALUES (?, ?, ?, ?, ?)",
                (g.user["id"], mat_name, json.dumps(symbols), json.dumps(layer_data), json.dumps(thicknesses))
            )
            db.commit()
            return redirect(url_for("spsplot.index"))
    
    return render_template("spsplot/add_target.html")

def get_target_material(id: int, check_user: bool = True) -> Any:
    db = get_db()
    mat = db.execute(
        "SELECT * FROM target_material t WHERE t.id = ?",
        (id,)
    ).fetchone()

    if mat is None:
        abort(404, f"Requested target material {id} does not exist")
    if check_user and mat["user_id"] != g.user["id"]:
        abort(403)
    return mat

@bp.route("/target/<int:id>/update", methods=("GET", "POST"))
@login_required
def update_target_material(id: int) -> Union[str, Response]:
    mat = get_target_material(id)
    if request.method == "POST":
        layer_data: list[list[tuple[int, int]]] = [[], [], []] #list of all layers
        thicknesses: list[float] = [] #thickness of all layers
        symbols: list[str] = [] #layer symbols
        mat_name = request.form["mat_name"]
        error = None
        #Retrive data from all layers
        db = get_db()
        for i in range(1, 4):
            thicknesses.append(request.form[f"layer{i}_thickness"])
            symbol = ""
            for j in range(1, 4):
                z = request.form[f"layer{i}_z{j}"]
                a = request.form[f"layer{i}_a{j}"]
                s = request.form[f"layer{i}_s{j}"]
                if z != "" and a != "" and s != "":
                    nucleus  = db.execute("SELECT id, element, isotope FROM nucleus n WHERE n.id = ?", (get_nucleus_id(int(z), int(a)),)).fetchone()
                    symbol += f"{nucleus['isotope']}<sub>{s}</sub>"
                    layer_data[i].append((get_nucleus_id(int(z), int(a)), s))
            if symbol != "":
                symbols.append(symbol)

        if mat_name is None:
            error = "Target material must have a name"

        if error is not None:
            flash(error)
        else:
            db.execute(
                "UPDATE target_material SET mat_name=?, mat_symbol=?, compounds=?, thicknesses=? WHERE id=?",
                (mat_name, json.dumps(symbols), json.dumps(layer_data), json.dumps(thicknesses), id)
            )
            db.commit()
            return redirect(url_for("spsplot.index"))
    
    return render_template("spsplot/update_target.html", mat=mat)

@bp.route("/target/<int:id>/delete", methods=("GET", "POST"))
@login_required
def delete_target_material(id: int) -> Response:
    get_target_material(id)
    db = get_db()
    db.execute("DELETE FROM target_material WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("spsplot.index"))

@bp.route("/rxn/add", methods=("GET", "POST"))
@login_required
def add_rxn() -> Union[str, Response]:
    db = get_db()
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

            testNuc = db.execute(
                "SELECT isotope, element, A FROM nucleus WHERE id IN (?, ?, ?, ?) ORDER BY CASE id WHEN ? THEN 1 WHEN ? THEN 2 WHEN ? THEN 3 WHEN ? THEN 4 END",
                (targID, projID, ejectID, residID, targID, projID, ejectID, residID)
            ).fetchall()
            if len(testNuc) != 4 or (projID == ejectID and len(testNuc) != 2):
                error = f"Only found {testNuc} of requested nuclei"

            if error is not None:
                flash(error)
            else:
                rxn_symbol = f"{testNuc[0]['isotope']}({testNuc[1]['isotope']},{testNuc[2]['isotope']}){testNuc[3]['isotope']}"
                latex_symbol = "$^{" + str(testNuc[0]['A']) + "}$" + testNuc[0]['element'] + \
                               "($^{" + str(testNuc[1]['A']) + "}$" + testNuc[1]['element'] + \
                               ",$^{" + str(testNuc[2]['A']) + "}$" + testNuc[2]['element'] + \
                               ")$^{" + str(testNuc[3]['A']) + "}$" + testNuc[3]['element']
                excitations = json.dumps(get_excitations(residID))
                db.execute(
                    "INSERT INTO reaction (user_id, target_mat_id, rxn_symbol, latex_rxn_symbol, target_nuc_id, projectile_nuc_id, ejectile_nuc_id, residual_nuc_id, excitations) VALUES (?,?,?,?,?,?,?,?,?)",
                    (g.user["id"], mat_id, rxn_symbol, latex_symbol, targID, projID, ejectID, residID, excitations)
                )
                db.commit()
                return redirect(url_for("spsplot.index"))
    
    target_mats = db.execute(
        "SELECT * FROM target_material t WHERE t.user_id = ?",
        (g.user["id"],)
    ).fetchall()

    return render_template("spsplot/add_rxn.html", target_mats=target_mats)

def get_rxn(id: int, check_user: bool = True) -> Any:
    db = get_db()
    rxn = db.execute(
        "SELECT * FROM reaction r WHERE r.id = ?",
        (id,)
    ).fetchone()

    if rxn is None:
        abort(404, f"Requested reaction {id} does not exist")
    if check_user and rxn["user_id"] != g.user["id"]:
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
    get_rxn(id)
    db = get_db()
    db.execute("DELETE FROM reaction WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("spsplot.index"))
