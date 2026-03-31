from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from models import Trabajadora, BoletaTrabajadora
from utils.time import hoy_peru, ahora_peru
from services.core_service import calcular_boleta
from extensions import db

from datetime import date, timedelta
import math

boletas_bp = Blueprint("boletas", __name__)

@boletas_bp.route("/boleta_trabajadora", methods=["GET","POST"])
def boleta_trabajadora():

    if session.get("rol") != "admin":
        return redirect(url_for("dashboard.dashboard"))

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

        t = db.session.get(Trabajadora, tid)

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

            return redirect(url_for("boletas.boleta_trabajadora", ver=tid, mes=mes_sel, q=quincena_sel))

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

        return redirect(url_for("boletas.boleta_trabajadora", ver=tid, mes=mes_sel, q=quincena_sel))

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


@boletas_bp.route("/cerrar_quincena")
def cerrar_quincena():

    if session.get("rol") != "admin":
        return redirect(url_for("dashboard.dashboard"))

    mes_sel = request.args.get("mes")
    q = request.args.get("q")

    if not mes_sel or not q:
        flash("Faltan parámetros","danger")
        return redirect(url_for("boletas.boleta_trabajadora"))

    anio = int(mes_sel.split("-")[0])
    mes = int(mes_sel.split("-")[1])
    q = int(q)

    if q == 1:
        inicio = date(anio, mes, 1)
    else:
        inicio = date(anio, mes, 16)

    boletas = BoletaTrabajadora.query.filter(
        BoletaTrabajadora.fecha_inicio == inicio,
        BoletaTrabajadora.cerrada == False
    ).all()

    if not boletas:
        flash("No hay boletas para cerrar ⚠️","warning")
        return redirect(url_for("boletas.boleta_trabajadora", mes=mes_sel, q=q))

    for b in boletas:
        b.cerrada = True
        b.fecha_cierre = ahora_peru()

    db.session.commit()

    flash("Quincena cerrada correctamente 🔒","success")
    return redirect(url_for("boletas.boleta_trabajadora", mes=mes_sel, q=q))


@boletas_bp.route("/boleta_pdf/<int:trabajadora_id>")
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
    c.drawString(50, y, f"Tardanzas: S/ {b.tardanzas}"); y-=20
    c.drawString(50, y, f"Faltas: S/ {b.faltas}"); y-=20
    c.drawString(50, y, f"Adelantos: S/ {b.adelantos}"); y-=20
    c.drawString(50, y, f"Descuentos: S/ {b.descuentos_manual}"); y-=30

    c.drawString(50, y, f"TOTAL A PAGAR: S/ {b.total_pagar}")

    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(buffer, download_name="boleta.pdf", mimetype="application/pdf")