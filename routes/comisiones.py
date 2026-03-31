from flask import Blueprint, request, render_template, redirect, session, flash
from datetime import datetime
from models import Venta
from extensions import db

comisiones_bp = Blueprint("comisiones", __name__)

# ================= PREVIEW RECALCULO =================

@comisiones_bp.route("/admin/recalcular_comisiones", methods=["POST"])
def preview_recalculo():

    if session.get("rol") != "admin":
        return redirect("/")

    desde = request.form["desde"]
    desde_dt = datetime.strptime(desde,"%Y-%m-%d")

    ventas = Venta.query.filter(Venta.fecha >= desde_dt).all()

    cambios = []

    for v in ventas:

        t = v.trabajadora
        total = v.precio

        comision = 0

        if t.tipo_pago == "porcentaje":
            comision = total * (t.comision/100)

        elif t.tipo_pago == "meta":

            if total >= t.meta_2:
                comision = total * (t.comision_meta_2/100)

            elif total >= t.meta_1:
                comision = total * (t.comision_meta_1/100)

        cambios.append({
            "venta": v.id,
            "trabajadora": t.nombre,
            "fecha": v.fecha.date(),
            "precio": total,
            "nueva_comision": round(comision,2)
        })

    return render_template(
        "preview_recalculo.html",
        cambios=cambios,
        desde=desde
    )


# ================= APLICAR RECALCULO =================

@comisiones_bp.route("/admin/aplicar_recalculo", methods=["POST"])
def aplicar_recalculo():

    if session.get("rol") != "admin":
        return redirect("/")

    desde = request.form["desde"]
    desde_dt = datetime.strptime(desde,"%Y-%m-%d")

    ventas = Venta.query.filter(Venta.fecha >= desde_dt).all()

    for v in ventas:

        t = v.trabajadora
        total = v.precio
        comision = 0

        if t.tipo_pago == "porcentaje":
            comision = total * (t.comision/100)

        elif t.tipo_pago == "meta":

            if total >= t.meta_2:
                comision = total * (t.comision_meta_2/100)

            elif total >= t.meta_1:
                comision = total * (t.comision_meta_1/100)

        v.comision = round(comision,2)

    db.session.commit()

    flash("Recalculo aplicado correctamente ✅","success")

    return redirect("/admin/trabajadoras")