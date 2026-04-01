from flask import Blueprint, render_template, redirect, session

from services.core_service import trabajadoras_activas
from services.venta_service import obtener_ventas
from services.servicio_service import obtener_servicios

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():

    if "user_id" not in session:
        return redirect("/login")

    ventas = obtener_ventas()
    trabajadoras = trabajadoras_activas()
    servicios = obtener_servicios()

    return render_template(
        "index.html",
        ventas=ventas,
        trabajadoras=trabajadoras,
        servicios=servicios
    )