# ================= IMPORTS PRINCIPALES =================

from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy

# ================= UTILIDADES FECHA =================

from datetime import datetime, date
from zoneinfo import ZoneInfo
from utils.time import ahora_peru, hoy_peru  # funciones centralizadas (evita circular imports)

# ================= SQL / QUERIES =================

from sqlalchemy import func, extract

# ================= SERVICES (LÓGICA DE NEGOCIO) =================

from services.kpi_service import obtener_kpis
from services.core_service import (
    trabajadoras_activas,
    servicios_ordenados,
    calcular_boleta
)
from services.dashboard_service import obtener_ventas_hoy

# ================= MODELOS =================

from models import (
    Trabajadora,
    Venta,
    Servicio,
    Usuario,
    Asistencia,
    Boleta,
    Factura,
    BoletaTrabajadora
)

# ================= CONFIGURACIÓN APP =================

app = Flask(__name__)  # instancia principal de Flask
app.secret_key = "clave_secreta_123"  # necesario para sesiones (login, flash, etc)

# ================= BASE DE DATOS =================

import os
from extensions import db  # instancia global de SQLAlchemy (patrón correcto)

db_url = os.environ.get("DATABASE_URL")  # Railway inyecta esta variable

if not db_url:
    raise RuntimeError("DATABASE_URL no está definido en Railway")

# fix para compatibilidad con SQLAlchemy 2+
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url  # configurar conexión DB

db.init_app(app)  # enlazar DB con Flask

# ================= TIMEZONE =================

PERU_TZ = ZoneInfo("America/Lima")  # zona horaria del sistema

# ================= BLUEPRINTS =================

from routes.dashboard import dashboard_bp  # importar rutas modularizadas
from routes.ventas import ventas_bp
from routes.trabajadoras import trabajadoras_bp
from routes.asistencia import asistencia_bp
from routes.servicios import servicios_bp
from routes.usuarios import usuarios_bp
from routes.comprobantes import comprobantes_bp
from routes.reportes import reportes_bp
from routes.graficos import graficos_bp
from routes.boletas import boletas_bp

app.register_blueprint(boletas_bp)
app.register_blueprint(graficos_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(comprobantes_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(servicios_bp)
app.register_blueprint(asistencia_bp)
app.register_blueprint(trabajadoras_bp)
app.register_blueprint(dashboard_bp)  # registrar rutas en la app
app.register_blueprint(ventas_bp)  # registrar rutas en la app



# ================= 

from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload
from datetime import date, timedelta
from sqlalchemy import extract
import math

# -------- RUTAS --------

@app.route("/")
def index():

    if "user_id" not in session:
        return redirect("/login")

    ventas = Venta.query.all()
    trabajadoras = trabajadoras_activas()
    servicios = Servicio.query.order_by(Servicio.nombre.asc()).all()

    return render_template(
        "index.html",
        ventas=ventas,
        trabajadoras=trabajadoras,
        servicios=servicios
    )

from flask import flash, redirect, request

    
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        user = Usuario.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()

        if user:
            session["user_id"] = user.id
            session["rol"] = user.rol
            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route('/comisiones')
def comisiones():
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")

    if not desde or not hasta:
        return "Usa ?desde=2026-01-01&hasta=2026-01-15"

    desde = datetime.strptime(desde, "%Y-%m-%d")
    hasta = datetime.strptime(hasta, "%Y-%m-%d")

    resultado = []

    trabajadoras = trabajadoras_activas()

    for t in trabajadoras:
        ventas = Venta.query.filter(
            Venta.trabajadora_id == t.id,
            Venta.fecha >= desde,
            Venta.fecha <= hasta
        ).all()

        total = sum(v.precio for v in ventas)

        comision_total = 0

        if t.tipo_pago == "porcentaje":
            comision_total = total * (t.comision / 100)

        elif t.tipo_pago == "meta":
            if total >= t.meta_2:
                comision_total = total * (t.comision_meta_2 / 100)
            elif total >= t.meta_1:
                comision_total = total * (t.comision_meta_1 / 100)

        pago = t.sueldo_base + comision_total

        resultado.append({
            "nombre": t.nombre,
            "ventas": total,
            "comision": comision_total,
            "pago": pago
        })

    return {"resultado": resultado}

from sqlalchemy import extract, func
from datetime import datetime

@app.route("/admin/recalcular_comisiones", methods=["POST"])
def preview_recalculo():

    from datetime import datetime
    import math

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

@app.route("/admin/aplicar_recalculo", methods=["POST"])
def aplicar_recalculo():

    from datetime import datetime

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
