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
from routes.comisiones import comisiones_bp
from routes.auth import auth_bp

app.register_blueprint(auth_bp)
app.register_blueprint(comisiones_bp)
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