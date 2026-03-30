from flask import Blueprint, render_template, request, redirect, session, flash
from models import Trabajadora, Asistencia
from extensions import db
from utils.time import ahora_peru, hoy_peru
import math

asistencia_bp = Blueprint("asistencia", __name__)

@asistencia_bp.route("/marcar", methods=["GET","POST"])
def marcar():

    from datetime import datetime

    trabajadoras = Trabajadora.query.filter_by(activo=True).order_by(Trabajadora.nombre).all()

    if request.method == "POST":

        trabajadora_id = int(request.form["trabajadora"])
        ahora = ahora_peru()

        fecha = ahora.date()
        hora_ingreso = ahora.time()
        dia_semana = ahora.weekday()

        # 🚫 domingo bloqueado
        if dia_semana == 6:
            flash("Domingo es día libre ☀️","info")
            return redirect("/marcar")

        ya = Asistencia.query.filter_by(
            trabajadora_id=trabajadora_id,
            fecha=fecha
        ).first()

        if ya:
            flash("Ya marcaste hoy ❌","danger")
            return redirect("/marcar")

        t = Trabajadora.query.get(trabajadora_id)

        # horario dinámico
        if dia_semana == 5:
            hora_oficial = t.hora_sabado
        else:
            hora_oficial = t.hora_semana

        dt_real = datetime.combine(fecha, hora_ingreso)
        dt_oficial = datetime.combine(fecha, hora_oficial)

        minutos = int((dt_real - dt_oficial).total_seconds()/60)
        minutos_tarde = max(0, minutos - 10)

        bloques = math.ceil(minutos_tarde / 10) if minutos_tarde > 0 else 0
        penalidad = bloques * 5

        nueva = Asistencia(
            fecha=fecha,
            hora_ingreso=hora_ingreso,
            minutos_tarde=minutos_tarde,
            penalidad=penalidad,
            trabajadora_id=trabajadora_id
        )

        db.session.add(nueva)
        db.session.commit()

        flash("Asistencia registrada ✅","success")
        return redirect("/marcar")

    return render_template("marcar.html", trabajadoras=trabajadoras)

@asistencia_bp.route("/asistencia_admin", methods=["GET","POST"])
def asistencia_admin():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import date, timedelta, datetime
    from sqlalchemy import extract

    accion = request.form.get("accion")
    edit_id = request.args.get("edit")

    # ================= EDITAR =================
    if request.method == "POST" and accion == "editar":

        a = Asistencia.query.get(request.form["id"])

        hora = request.form.get("hora")

        if hora:
            try:
                a.hora_ingreso = datetime.strptime(hora, "%H:%M").time()
            except:
                a.hora_ingreso = datetime.strptime(hora, "%H:%M:%S").time()

        trab = a.trabajadora

        if a.fecha.weekday() == 5:
            hora_oficial = trab.hora_sabado
        else:
            hora_oficial = trab.hora_semana

        dt_real = datetime.combine(a.fecha, a.hora_ingreso)
        dt_oficial = datetime.combine(a.fecha, hora_oficial)

        minutos = int((dt_real - dt_oficial).total_seconds()/60)
        minutos_tarde = max(0, minutos - 10)

        bloques = math.ceil(minutos_tarde / 10) if minutos_tarde > 0 else 0
        penalidad = bloques * 5

        a.minutos_tarde = minutos_tarde
        a.penalidad = penalidad

        db.session.commit()
        flash("Asistencia actualizada ✅","success")
        return redirect("/asistencia_admin")

    # ================= BORRAR =================
    if request.method == "POST" and accion == "borrar":

        a = Asistencia.query.get(request.form["id"])
        db.session.delete(a)
        db.session.commit()

        flash("Asistencia eliminada 🗑","warning")
        return redirect("/asistencia_admin")

    # ================= LISTADO =================

    trabajadora_id = request.args.get("trabajadora")
    mes_sel = request.args.get("mes")

    trabajadoras = Trabajadora.query.filter_by(activo=True).all()
    hoy = hoy_peru()

    if mes_sel:
        anio, mes = map(int, mes_sel.split("-"))
    else:
        anio = hoy.year
        mes = hoy.month

    registros = Asistencia.query.filter(
        extract('year', Asistencia.fecha)==anio,
        extract('month', Asistencia.fecha)==mes
    ).all()

    total_penalidad = sum(r.penalidad for r in registros)

    t_edit = Asistencia.query.get(edit_id) if edit_id else None

    return render_template(
        "asistencia_admin.html",
        registros=registros,
        trabajadoras=trabajadoras,
        total_penalidad=total_penalidad,
        t_edit=t_edit
    )