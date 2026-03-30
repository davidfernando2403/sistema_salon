from flask import Blueprint, render_template, request, redirect, flash
from models import Boleta, Factura
from extensions import db
from datetime import datetime

comprobantes_bp = Blueprint("comprobantes", __name__)

@comprobantes_bp.route("/comprobantes", methods=["GET","POST"])
def comprobantes():

    if request.method == "POST":

        tipo = request.form["tipo"]
        codigo = request.form["codigo"]
        monto = float(request.form["monto"])
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()

        if tipo == "boleta":
            db.session.add(Boleta(codigo=codigo, monto=monto, fecha=fecha))
        else:
            db.session.add(Factura(codigo=codigo, monto=monto, fecha=fecha))

        db.session.commit()

        flash("Registrado correctamente ✅","success")

    boletas = Boleta.query.order_by(Boleta.fecha.desc()).all()
    facturas = Factura.query.order_by(Factura.fecha.desc()).all()

    return render_template("comprobantes.html", boletas=boletas, facturas=facturas)