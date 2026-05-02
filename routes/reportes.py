from flask import Blueprint, render_template, request, redirect, session
from models import Boleta, Factura
from extensions import db
from utils.time import ahora_peru
from services.kpi_service import obtener_kpis
from services.reportes_service import obtener_filtros_reportes
from services.core_service import trabajadoras_activas

from sqlalchemy import func, extract
from datetime import datetime, timedelta

reportes_bp = Blueprint("reportes", __name__)

@reportes_bp.route("/reportes")
def reportes():

    if "user_id" not in session:
        return redirect("/login")

    # ================= FILTROS =================
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")

    fecha_inicio = None
    fecha_fin = None

    if desde and hasta:
        fecha_inicio = datetime.strptime(desde, "%Y-%m-%d")
        fecha_fin = datetime.strptime(hasta, "%Y-%m-%d") + timedelta(days=1)

    # ================= KPIs =================
    data_kpis = obtener_kpis(fecha_inicio, fecha_fin)

    # ================= FILTROS LEGACY =================
    filtros = obtener_filtros_reportes(request.args)

    mes_kpi = request.args.get("mes_kpi")

    # Si no selecciona nada → mes actual
    if mes_kpi:
        año, mes = map(int, mes_kpi.split("-"))
    else:
        hoy = ahora_peru()
        año = hoy.year
        mes = hoy.month

    # ================= BOLETAS =================
    total_boletas = db.session.query(
        func.coalesce(func.sum(Boleta.monto), 0)
    ).filter(
        extract("year", Boleta.fecha) == año,
        extract("month", Boleta.fecha) == mes
    ).scalar()

    # ================= FACTURAS =================
    total_facturas = db.session.query(
        func.coalesce(func.sum(Factura.monto), 0)
    ).filter(
        extract("year", Factura.fecha) == año,
        extract("month", Factura.fecha) == mes
    ).scalar()

    return render_template(
        "reportes.html",
        **data_kpis,
        **filtros,
        trabajadoras=trabajadoras_activas(),
        total_boletas=round(total_boletas, 2),
        total_facturas=round(total_facturas, 2),
        mes_kpi=mes_kpi   # 👈 NUEVO
    )