from flask import Blueprint, render_template, request, redirect
from models.caja_movimiento import CajaMovimiento
from extensions import db
from sqlalchemy import func

caja_bp = Blueprint("caja", __name__)

@caja_bp.route("/caja", methods=["GET", "POST"])
def caja():

    # ================= REGISTRAR GASTO =================
    if request.method == "POST":
        monto = float(request.form["monto"])
        detalle = request.form["detalle"]

        movimiento = CajaMovimiento(
            tipo="egreso",
            monto=monto,
            detalle=detalle,
            origen="manual"
        )

        db.session.add(movimiento)
        db.session.commit()

        return redirect("/caja")

    # ================= OBTENER MOVIMIENTOS =================
    movimientos = CajaMovimiento.query.order_by(
        CajaMovimiento.fecha.desc()
    ).all()

    # ================= CALCULAR SALDO =================
    ingresos = sum(m.monto for m in movimientos if m.tipo == "ingreso")
    egresos = sum(m.monto for m in movimientos if m.tipo == "egreso")

    saldo = ingresos - egresos

    return render_template(
        "caja.html",
        movimientos=movimientos,
        saldo=saldo,
        ingresos=ingresos,
        egresos=egresos
    )