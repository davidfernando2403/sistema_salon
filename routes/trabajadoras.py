from flask import Blueprint, render_template, request, redirect, session, flash
from models import Trabajadora, Asistencia
from extensions import db
import math

trabajadoras_bp = Blueprint("trabajadoras", __name__)

@trabajadoras_bp.route("/admin/trabajadoras", methods=["GET","POST"])
def admin_trabajadoras():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import datetime, time

    accion = request.form.get("accion")
    edit_id = request.args.get("edit")

    t_edit = Trabajadora.query.get(edit_id) if edit_id else None

    # ================= CREAR =================
    if request.method == "POST" and accion == "crear":

        nueva = Trabajadora(
            nombre=request.form["nombre"],
            tipo_pago=request.form["tipo_pago"],
            sueldo_base=float(request.form.get("sueldo_base") or 0),
            comision=float(request.form.get("comision") or 0),
            meta_1=float(request.form.get("meta_1") or 0),
            comision_meta_1=float(request.form.get("comision_meta_1") or 0),
            meta_2=float(request.form.get("meta_2") or 0),
            comision_meta_2=float(request.form.get("comision_meta_2") or 0),
            activo=True,
            hora_semana=time(10,0),
            hora_sabado=time(10,0)
        )

        db.session.add(nueva)
        db.session.commit()

        flash("Trabajadora creada ✅","success")
        return redirect("/admin/trabajadoras")

    # ================= EDITAR =================
    if request.method == "POST" and accion == "editar":

        t = Trabajadora.query.get(request.form["id"])

        t.nombre = request.form["nombre"]
        t.tipo_pago = request.form["tipo_pago"]
        t.sueldo_base = float(request.form.get("sueldo_base") or 0)
        t.comision = float(request.form.get("comision") or 0)

        t.meta_1 = float(request.form.get("meta_1") or 0)
        t.comision_meta_1 = float(request.form.get("comision_meta_1") or 0)

        t.meta_2 = float(request.form.get("meta_2") or 0)
        t.comision_meta_2 = float(request.form.get("comision_meta_2") or 0)

        t.activo = True if request.form.get("activo") else False

        hora_semana = request.form.get("hora_semana")
        hora_sabado = request.form.get("hora_sabado")

        if hora_semana:
            t.hora_semana = time.fromisoformat(hora_semana)

        if hora_sabado:
            t.hora_sabado = time.fromisoformat(hora_sabado)

        db.session.commit()

        # 🔥 RECALCULO ASISTENCIAS
        asistencias = Asistencia.query.filter_by(trabajadora_id=t.id).all()

        for a in asistencias:

            fecha = a.fecha
            hora = a.hora_ingreso

            dia = fecha.weekday()

            if dia == 5:
                hora_oficial = t.hora_sabado
            else:
                hora_oficial = t.hora_semana

            dt_real = datetime.combine(fecha, hora)
            dt_oficial = datetime.combine(fecha, hora_oficial)

            minutos = int((dt_real - dt_oficial).total_seconds()/60)
            minutos_tarde = max(0, minutos - 10)

            bloques = math.ceil(minutos_tarde / 10) if minutos_tarde > 0 else 0
            penalidad = bloques * 5

            a.minutos_tarde = minutos_tarde
            a.penalidad = penalidad

        db.session.commit()

        flash("Trabajadora actualizada y asistencias recalculadas ✅","success")
        return redirect("/admin/trabajadoras")

    lista = Trabajadora.query.order_by(Trabajadora.nombre).all()

    return render_template(
        "admin_trabajadoras.html",
        trabajadoras=lista,
        t_edit=t_edit
    )