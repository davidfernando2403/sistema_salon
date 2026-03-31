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
    from calendar import monthrange

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
        
    # ================= REGISTRO MANUAL =================
    if request.method == "POST" and accion == "manual":

        from datetime import datetime

        trabajadora_id = int(request.form["trabajadora"])
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()

        # validar domingo
        if fecha.weekday() == 6:
            flash("Domingo no se registra asistencia ❌", "warning")
            return redirect("/asistencia_admin")

        hora_str = request.form.get("hora")

        try:
            hora_ingreso = datetime.strptime(hora_str, "%H:%M").time()
        except:
            hora_ingreso = datetime.strptime(hora_str, "%H:%M:%S").time()

        # validar si ya existe
        existe = Asistencia.query.filter_by(
            trabajadora_id=trabajadora_id,
            fecha=fecha
        ).first()

        if existe:
            flash("Ya existe asistencia para ese día ❌", "danger")
            return redirect("/asistencia_admin")

        t = Trabajadora.query.get(trabajadora_id)

        # horario
        if fecha.weekday() == 5:
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

        flash("Asistencia registrada manualmente ✅", "success")

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

    trabajadora_id = request.args.get("trabajadora")
    quincena = request.args.get("quincena")

    query = Asistencia.query.filter(
        extract('year', Asistencia.fecha) == anio,
        extract('month', Asistencia.fecha) == mes
    )

    # ================= FILTRO TRABAJADORA =================
    if trabajadora_id and trabajadora_id != "todas":
        query = query.filter(Asistencia.trabajadora_id == int(trabajadora_id))

    # ================= FILTRO QUINCENA =================
    if quincena == "1":
        query = query.filter(extract('day', Asistencia.fecha) <= 15)

    elif quincena == "2":
        query = query.filter(extract('day', Asistencia.fecha) >= 16)

    registros = query.order_by(Asistencia.fecha.desc()).all()

    total_penalidad = sum(r.penalidad for r in registros)

    t_edit = Asistencia.query.get(edit_id) if edit_id else None

    # ================= NUEVO: DIAS SIN MARCAR =================

    _, ultimo_dia = monthrange(anio, mes)

    fechas = [date(anio, mes, d) for d in range(1, ultimo_dia + 1)]

    # mapa de asistencias
    asistencias_map = {
        (r.trabajadora_id, r.fecha): True
        for r in registros
    }

    faltas_tabla = {}

    for f in fechas:

        faltas_tabla[f] = {}

        for t in trabajadoras:

            # 🚫 domingo → nunca marcar falta
            if f.weekday() == 6:
                faltas_tabla[f][t.nombre] = False
                continue

            key = (t.id, f)

            # True = falta (mostrar ❌)
            faltas_tabla[f][t.nombre] = key not in asistencias_map

    # ================= RETURN =================

    return render_template(
        "asistencia_admin.html",
        registros=registros,
        trabajadoras=trabajadoras,
        total_penalidad=total_penalidad,
        t_edit=t_edit,
        trabajadora_id=trabajadora_id,
        mes_sel=f"{anio}-{str(mes).zfill(2)}",
        quincena=quincena,
        fechas=fechas,                # 👈 NUEVO
        faltas_tabla=faltas_tabla     # 👈 NUEVO
    )