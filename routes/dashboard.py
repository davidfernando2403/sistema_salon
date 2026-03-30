from flask import Blueprint, render_template, redirect, session
from utils.time import ahora_peru, hoy_peru
from services.kpi_service import obtener_kpis
from services.dashboard_service import obtener_ventas_hoy

from models import Venta, Boleta
from extensions import db
from sqlalchemy import func, extract

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    from models import Trabajadora
    from services.core_service import trabajadoras_activas

    hoy = ahora_peru()
    hoy_date = hoy_peru()

    # ================= MES EN ESPAÑOL =================
    MESES_ES = {
        1: "Enero", 2: "Febrero", 3: "Marzo",
        4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre",
        10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    nombre_mes = f"{MESES_ES[hoy.month]} {hoy.year}"

    # ================= MES ACTUAL =================
    total_mes_actual = db.session.query(
        func.coalesce(func.sum(Venta.precio), 0)
    ).filter(
        extract("year", Venta.fecha) == hoy.year,
        extract("month", Venta.fecha) == hoy.month
    ).scalar()

    # ================= BOLETAS MES ACTUAL =================
    total_boletas_mes_actual = db.session.query(
        func.coalesce(func.sum(Boleta.monto), 0)
    ).filter(
        extract("year", Boleta.fecha) == hoy.year,
        extract("month", Boleta.fecha) == hoy.month
    ).scalar()

    # ================= QUINCENA =================
    from datetime import datetime

    if hoy.day <= 15:
        inicio = datetime(hoy.year, hoy.month, 1)
        fin = datetime(hoy.year, hoy.month, 15)
        titulo_quincena = "1–15"
    else:
        inicio = datetime(hoy.year, hoy.month, 16)
        fin = datetime(hoy.year, hoy.month, 31)
        titulo_quincena = "16–fin de mes"

    # ================= KPIs =================
    data_kpis = obtener_kpis(inicio, fin)
    total_quincena = data_kpis.get("total_general", 0)

    # ================= HOY =================
    resumen_hoy, total_hoy = obtener_ventas_hoy(hoy_date)
    resumen_hoy = dict(sorted(resumen_hoy.items(), key=lambda x: x[1], reverse=True))
    total_hoy = sum(resumen_hoy.values())

    return render_template(
        "dashboard.html",
        titulo_quincena=titulo_quincena,
        resumen_hoy=resumen_hoy,
        total_hoy=round(total_hoy, 2),
        trabajadoras=trabajadoras_activas(),
        total_mes_actual=round(total_mes_actual, 2),
        total_boletas_mes_actual=round(total_boletas_mes_actual, 2),
        total_quincena=round(total_quincena, 2),
        nombre_mes=nombre_mes,
        **data_kpis
    )