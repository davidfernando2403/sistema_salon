from flask import Blueprint, render_template, request, redirect, session
from models import Servicio
from extensions import db

servicios_bp = Blueprint("servicios", __name__)

@servicios_bp.route("/servicios")
def servicios():

    if session.get("rol") != "admin":
        return redirect("/")

    lista = Servicio.query.order_by(Servicio.nombre.asc()).all()

    return render_template("servicios.html", servicios=lista)

@servicios_bp.route("/servicios/agregar", methods=["POST"])
def agregar_servicio():

    if session.get("rol") != "admin":
        return redirect("/")

    nombre = request.form["nombre"]

    nuevo = Servicio(nombre=nombre)
    db.session.add(nuevo)
    db.session.commit()

    return redirect("/servicios")

@servicios_bp.route("/servicios/editar/<int:id>", methods=["POST"])
def editar_servicio(id):

    if session.get("rol") != "admin":
        return redirect("/")

    servicio = Servicio.query.get(id)
    servicio.nombre = request.form["nombre"]

    db.session.commit()

    return redirect("/servicios")

@servicios_bp.route("/servicios/eliminar/<int:id>")
def eliminar_servicio(id):

    if session.get("rol") != "admin":
        return redirect("/")

    servicio = Servicio.query.get(id)

    db.session.delete(servicio)
    db.session.commit()

    return redirect("/servicios")