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
      
@app.route("/reportes")
def reportes():

    if "user_id" not in session:
        return redirect("/login")

    from datetime import datetime, timedelta
    from sqlalchemy import func, extract

    # ================= FILTROS =================
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")

    fecha_inicio = None
    fecha_fin = None

    if desde and hasta:
        fecha_inicio = datetime.strptime(desde, "%Y-%m-%d")
        fecha_fin = datetime.strptime(hasta, "%Y-%m-%d") + timedelta(days=1)

    # ================= NUEVO KPI =================
    data_kpis = obtener_kpis(fecha_inicio, fecha_fin)

    # ================= MANTENER LO ANTIGUO =================
    from services.reportes_service import obtener_filtros_reportes

    filtros = obtener_filtros_reportes(request.args)
    
    hoy = ahora_peru()

    # ================= BOLETAS MES ACTUAL =================
    total_boletas = db.session.query(
        func.coalesce(func.sum(Boleta.monto), 0)
    ).filter(
        extract("year", Boleta.fecha) == hoy.year,
        extract("month", Boleta.fecha) == hoy.month
    ).scalar()

    # ================= FACTURAS MES ACTUAL =================
    total_facturas = db.session.query(
        func.coalesce(func.sum(Factura.monto), 0)
    ).filter(
        extract("year", Factura.fecha) == hoy.year,
        extract("month", Factura.fecha) == hoy.month
    ).scalar()

    return render_template(
        "reportes.html",
        **data_kpis,   # 🔥 nuevo
        **filtros,     # 🔥 antiguo (no romper)
        trabajadoras=trabajadoras_activas(),
        total_boletas=round(total_boletas, 2),
        total_facturas=round(total_facturas, 2)
    )

@app.route("/graficos")
def graficos():

    if "user_id" not in session:
        return redirect("/login")

    from datetime import datetime
    from sqlalchemy import extract, func

    hoy = ahora_peru()

    mes_sel = request.args.get("mes") or f"{hoy.year}-{str(hoy.month).zfill(2)}"
    anio = int(mes_sel.split("-")[0])
    mes = int(mes_sel.split("-")[1])

    # ================= 1. VENTAS POR DIA =================

    ventas = db.session.query(
        extract("day", Venta.fecha),
        func.sum(Venta.precio)
    ).filter(
        extract("year", Venta.fecha)==anio,
        extract("month", Venta.fecha)==mes
    ).group_by(
        extract("day", Venta.fecha)
    ).order_by(
        extract("day", Venta.fecha)
    ).all()

    dias = [int(d) for d,_ in ventas]
    totales_dia = [float(t or 0) for _,t in ventas]

    # ================= 2. PRODUCCION POR TRABAJADORA =================

    produccion = db.session.query(
        extract("day", Venta.fecha),
        Trabajadora.nombre,
        func.sum(Venta.precio)
    ).join(Trabajadora).filter(
        extract("year", Venta.fecha)==anio,
        extract("month", Venta.fecha)==mes
    ).group_by(
        extract("day", Venta.fecha),
        Trabajadora.nombre
    ).all()

    prod_dict = {}

    for d,nombre,total in produccion:
        prod_dict.setdefault(nombre,{})
        prod_dict[nombre][int(d)] = float(total or 0)

    prod_labels = sorted({d for datos in prod_dict.values() for d in datos.keys()})

    prod_datasets = []

    for nombre,datos in prod_dict.items():
        fila = [datos.get(d,0) for d in prod_labels]

        prod_datasets.append({
            "label": nombre,
            "data": fila
        })

    # ================= 3. PRODUCCION MES A MES =================

    produccion_mes = db.session.query(
        extract("year",Venta.fecha),
        extract("month",Venta.fecha),
        func.sum(Venta.precio)
    ).group_by(
        extract("year",Venta.fecha),
        extract("month",Venta.fecha)
    ).order_by(
        extract("year",Venta.fecha),
        extract("month",Venta.fecha)
    ).all()

    meses_labels = [f"{int(y)}-{str(int(m)).zfill(2)}" for y,m,_ in produccion_mes]
    meses_totales = [float(t or 0) for _,_,t in produccion_mes]

# ================= 4. SERVICIOS =================

    mes_serv = request.args.get("mes_servicios") or mes_sel
    orden = request.args.get("orden") or "cantidad"

    anio_serv = int(mes_serv.split("-")[0])
    mes_serv_num = int(mes_serv.split("-")[1])

    servicios = db.session.query(
        Servicio.nombre,
        func.count(Venta.id).label("cantidad"),
        func.sum(Venta.precio).label("total")
    ).join(Venta).filter(
        extract("year", Venta.fecha)==anio_serv,
        extract("month", Venta.fecha)==mes_serv_num
    ).group_by(Servicio.nombre).all()

    # Convertir a lista manejable
    servicios = [
        {
            "nombre": s[0],
            "cantidad": int(s[1] or 0),
            "total": float(s[2] or 0)
        }
        for s in servicios
    ]

    # Orden dinámico
    if orden == "total":
        servicios.sort(key=lambda x: x["total"], reverse=True)
    else:
        servicios.sort(key=lambda x: x["cantidad"], reverse=True)

    serv_nombres = [s["nombre"] for s in servicios]
    serv_cantidad = [s["cantidad"] for s in servicios]
    serv_totales = [s["total"] for s in servicios]

# ================= 5. METODO DE PAGO =================

    mes_pagos = request.args.get("mes_pagos") or mes_sel

    anio_p = int(mes_pagos.split("-")[0])
    mes_p = int(mes_pagos.split("-")[1])

    pagos = db.session.query(
        func.lower(Venta.medio_pago),
        func.sum(Venta.precio)
    ).filter(
        extract("year",Venta.fecha)==anio_p,
        extract("month",Venta.fecha)==mes_p
    ).group_by(
        func.lower(Venta.medio_pago)
    ).all()

    pago_labels = [p[0].capitalize() for p in pagos]
    pago_totales = [float(p[1] or 0) for p in pagos]
    
    top_servicios = servicios[:10]

    return render_template(
        "graficos.html",
        mes_sel=mes_sel,

        dias=dias,
        totales_dia=totales_dia,

        prod_labels=prod_labels,
        prod_datasets=prod_datasets,

        meses_labels=meses_labels,
        meses_totales=meses_totales,

        serv_nombres=serv_nombres,
        serv_cantidad=serv_cantidad,
        serv_totales=serv_totales,

        pago_labels=pago_labels,
        pago_totales=pago_totales,
        
        orden=orden,
        mes_serv=mes_serv,
        
        servicios=servicios,
        top_servicios=top_servicios,
        
        mes_pagos=mes_pagos
    )

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

@app.route("/boleta_trabajadora", methods=["GET","POST"])
def boleta_trabajadora():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import date, timedelta

    mes_sel = request.args.get("mes")
    quincena_sel = request.args.get("q")

    hoy = hoy_peru()

    # ================= CALCULAR PERIODO =================

    if mes_sel and quincena_sel:

        anio = int(mes_sel.split("-")[0])
        mes = int(mes_sel.split("-")[1])
        q = int(quincena_sel)

        if q == 1:
            inicio = date(anio, mes, 1)
            fin = date(anio, mes, 15)
            titulo = "1–15"
        else:
            inicio = date(anio, mes, 16)
            siguiente = date(anio + (mes == 12), ((mes) % 12) + 1, 1)
            fin = siguiente - timedelta(days=1)
            titulo = "16–fin"

    else:

        if hoy.day <= 15:
            inicio = date(hoy.year, hoy.month, 1)
            fin = date(hoy.year, hoy.month, 15)
            titulo = "1–15"
        else:
            inicio = date(hoy.year, hoy.month, 16)
            siguiente = date(hoy.year + (hoy.month == 12), ((hoy.month) % 12) + 1, 1)
            fin = siguiente - timedelta(days=1)
            titulo = "16–fin"

    trabajadoras = Trabajadora.query.filter_by(activo=True).all()

    edit_id = request.args.get("edit")
    edit_id = int(edit_id) if edit_id else None

    ver_id = request.args.get("ver")
    ver_id = int(ver_id) if ver_id else None

    hist = request.args.get("hist")

    # ================= POST =================

    if request.method == "POST":

        accion = request.form.get("accion")
        tid = int(request.form["trabajadora_id"])

        t = Trabajadora.query.get(tid)

        boleta = BoletaTrabajadora.query.filter_by(
            trabajadora_id=tid,
            fecha_inicio=inicio,
            fecha_fin=fin
        ).first()

        if not boleta:
            boleta = BoletaTrabajadora(
                trabajadora_id=tid,
                fecha_inicio=inicio,
                fecha_fin=fin
            )

        # ===== RECALCULAR =====

        if accion == "recalcular":

            r_calc = calcular_boleta(t, inicio, fin)

            boleta.sueldo_base = r_calc.get("sueldo", 0)
            boleta.comisiones = r_calc.get("comision", 0)
            boleta.tardanzas = r_calc.get("tardanzas", 0)
            boleta.faltas = r_calc.get("faltas", 0)

            ingresos = (boleta.sueldo_base or 0) + (boleta.comisiones or 0) + (boleta.bonos or 0)
            egresos = (
                (boleta.tardanzas or 0)
                + (boleta.faltas or 0)
                + (boleta.adelantos or 0)
                + (boleta.descuentos_manual or 0)
            )

            boleta.subtotal_ingresos = ingresos
            boleta.subtotal_descuentos = egresos
            boleta.total_pagar = ingresos - egresos

            boleta.modificada_manual = False

            db.session.add(boleta)
            db.session.commit()

            flash("Valores recalculados automáticamente ✅", "info")

            if mes_sel and quincena_sel:
                return redirect(f"/boleta_trabajadora?ver={tid}&mes={mes_sel}&q={quincena_sel}")
            else:
                return redirect(f"/boleta_trabajadora?ver={tid}")

        # ===== GUARDAR EDICIÓN =====

        sueldo = float(request.form.get("sueldo") or 0)
        comision = float(request.form.get("comision") or 0)
        bonos = float(request.form.get("bonos") or 0)
        adelantos = float(request.form.get("adelantos") or 0)
        descuentos = float(request.form.get("descuentos") or 0)
        tardanzas = float(request.form.get("tardanzas") or 0)
        faltas = float(request.form.get("faltas") or 0)

        r_calc = calcular_boleta(t, inicio, fin)
        tardanzas_auto = r_calc.get("tardanzas", 0)
        faltas_auto = r_calc.get("faltas", 0)

        modificada = (tardanzas != tardanzas_auto) or (faltas != faltas_auto)

        ingresos = sueldo + comision + bonos
        egresos = tardanzas + faltas + adelantos + descuentos
        total = ingresos - egresos

        boleta.sueldo_base = sueldo
        boleta.comisiones = comision
        boleta.bonos = bonos
        boleta.adelantos = adelantos
        boleta.descuentos_manual = descuentos
        boleta.tardanzas = tardanzas
        boleta.faltas = faltas
        boleta.subtotal_ingresos = ingresos
        boleta.subtotal_descuentos = egresos
        boleta.total_pagar = total
        boleta.modificada_manual = modificada

        db.session.add(boleta)
        db.session.commit()

        flash("Boleta actualizada ✅","success")

        if mes_sel and quincena_sel:
            return redirect(f"/boleta_trabajadora?ver={tid}&mes={mes_sel}&q={quincena_sel}")
        else:
            return redirect(f"/boleta_trabajadora?ver={tid}")

    # ================= ARMAR TABLA =================

    filas = []

    for t in trabajadoras:

        r = calcular_boleta(t, inicio, fin)

        r["sueldo"] = round((t.sueldo_base or 0) / 2, 2)
        r["tardanzas"] = r.get("tardanzas", 0)
        r["faltas"] = r.get("faltas", 0)

        boleta = BoletaTrabajadora.query.filter_by(
            trabajadora_id=t.id,
            fecha_inicio=inicio,
            fecha_fin=fin
        ).first()

        r["bloqueada"] = True if (boleta and boleta.cerrada) else False

        if boleta:
            r["sueldo"] = boleta.sueldo_base
            r["comision"] = boleta.comisiones
            r["bonos"] = boleta.bonos
            r["adelantos"] = boleta.adelantos
            r["descuentos"] = boleta.descuentos_manual
            r["tardanzas"] = boleta.tardanzas
            r["faltas"] = boleta.faltas

        ingresos = r["sueldo"] + r["comision"] + r["bonos"]
        egresos = r["tardanzas"] + r["faltas"] + r["adelantos"] + r["descuentos"]
        r["total"] = ingresos - egresos

        filas.append({
            "id": t.id,
            "nombre": t.nombre,
            "modificada_manual": boleta.modificada_manual if boleta else False,
            **r
        })

    if ver_id:
        filas = [f for f in filas if f["id"] == ver_id]

    historicos = []

    if hist:
        historicos = BoletaTrabajadora.query.filter_by(cerrada=True)\
            .order_by(BoletaTrabajadora.fecha_inicio.desc())\
            .all()

    return render_template(
        "boleta_trabajadora.html",
        filas=filas,
        todas_trabajadoras=trabajadoras,
        inicio=inicio,
        fin=fin,
        titulo=titulo,
        edit_id=edit_id,
        ver_id=ver_id,
        historicos=historicos,
        hist=hist
    )

@app.route("/cerrar_quincena")
def cerrar_quincena():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import date, timedelta

    mes_sel = request.args.get("mes")
    q = request.args.get("q")

    if not mes_sel or not q:
        flash("Faltan parámetros","danger")
        return redirect("/boleta_trabajadora")

    anio = int(mes_sel.split("-")[0])
    mes = int(mes_sel.split("-")[1])
    q = int(q)

    if q == 1:
        inicio = date(anio, mes, 1)
        fin = date(anio, mes, 15)
    else:
        inicio = date(anio, mes, 16)
        siguiente = date(anio + (mes==12), ((mes)%12)+1, 1)
        fin = siguiente - timedelta(days=1)

    boletas = BoletaTrabajadora.query.filter(
        BoletaTrabajadora.fecha_inicio == inicio,
        BoletaTrabajadora.cerrada == False
    ).all()
    # 🔍 DEBUG
    print("Boletas encontradas:", len(boletas))
    for b in boletas:
        print(
            "Trabajadora:", b.trabajadora_id,
            "Inicio:", b.fecha_inicio,
            "Fin:", b.fecha_fin,
            "Cerrada:", b.cerrada
        )
        
    if not boletas:
        flash("No hay boletas para cerrar ⚠️","warning")
        return redirect(f"/boleta_trabajadora?mes={mes_sel}&q={q}")

    for b in boletas:
        b.cerrada = True
        b.fecha_cierre = ahora_peru()

    db.session.commit()

    flash("Quincena cerrada correctamente 🔒","success")
    return redirect(f"/boleta_trabajadora?mes={mes_sel}&q={q}")

@app.route("/boleta_pdf/<int:trabajadora_id>")
def boleta_pdf(trabajadora_id):

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from flask import send_file
    import io

    b = BoletaTrabajadora.query.filter_by(trabajadora_id=trabajadora_id)\
        .order_by(BoletaTrabajadora.id.desc()).first()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    y = 800
    c.drawString(50, y, "BOLETA DE PAGO"); y-=30
    c.drawString(50, y, f"Trabajadora: {b.trabajadora.nombre}"); y-=25
    c.drawString(50, y, f"Periodo: {b.fecha_inicio} - {b.fecha_fin}"); y-=30

    c.drawString(50, y, f"Sueldo: S/ {b.sueldo_base}"); y-=20
    c.drawString(50, y, f"Comisión: S/ {b.comisiones}"); y-=20
    c.drawString(50, y, f"Bonos: S/ {b.bonos}"); y-=20

    # 🔥 NUEVO
    c.drawString(50, y, f"Tardanzas: S/ {b.tardanzas}"); y-=20
    c.drawString(50, y, f"Faltas: S/ {b.faltas}"); y-=20

    c.drawString(50, y, f"Adelantos: S/ {b.adelantos}"); y-=20
    c.drawString(50, y, f"Descuentos: S/ {b.descuentos_manual}"); y-=30

    c.drawString(50, y, f"TOTAL A PAGAR: S/ {b.total_pagar}")

    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(buffer, download_name="boleta.pdf", mimetype="application/pdf")

