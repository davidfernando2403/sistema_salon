from flask import Blueprint, render_template, request, redirect, session, flash
from models import Venta, Servicio
from extensions import db
from utils.time import ahora_peru, hoy_peru
from services.core_service import trabajadoras_activas

ventas_bp = Blueprint("ventas", __name__)

@ventas_bp.route("/ventas/nueva")
def ventas_nueva():

    hoy = hoy_peru()

    ventas = Venta.query.filter(
        db.func.date(Venta.fecha) == hoy
    ).order_by(Venta.fecha.desc()).all()

    total_hoy = round(sum(v.precio for v in ventas), 2)

    return render_template(
        "venta_nueva.html",
        ventas=ventas,
        trabajadoras=trabajadoras_activas(),
        servicios=Servicio.query.order_by(Servicio.nombre.asc()).all(),
        total_hoy=total_hoy
    )
    
@ventas_bp.route("/ventas/guardar", methods=["POST"])
def ventas_guardar():

    from datetime import datetime

    try:
        fecha_form = request.form.get("fecha")

        if fecha_form:
            fecha = datetime.strptime(fecha_form, "%Y-%m-%d")
        else:
            fecha = ahora_peru()

        nueva = Venta(
            fecha=fecha,
            cliente=request.form['cliente'],
            precio=float(request.form['precio']),
            medio_pago=request.form['medio_pago'],
            dni=request.form.get('dni'),
            telefono=request.form.get('telefono'),
            observaciones=request.form.get('observaciones'),
            trabajadora_id=int(request.form['trabajadora']),
            servicio_id=int(request.form['servicio'])
        )

        db.session.add(nueva)
        db.session.commit()

        flash("Venta registrada correctamente ✅", "ventas")

    except Exception as e:
        db.session.rollback()
        flash("Error al registrar venta ❌", "danger")
        print(e)

    return redirect("/ventas/nueva")

@ventas_bp.route("/ventas")
def ventas():

    if session.get("rol") != "admin":
        return redirect("/")

    page = request.args.get("page", 1, type=int)

    campo = request.args.get("campo")
    q = request.args.get("q")
    fecha = request.args.get("fecha")

    if campo == "None":
        campo = None
    if q == "None":
        q = None
    if fecha == "None":
        fecha = None

    query = Venta.query

    if campo and q:

        if campo == "cliente":
            query = query.filter(Venta.cliente.ilike(f"%{q}%"))

        elif campo == "dni":
            query = query.filter(Venta.dni.ilike(f"%{q}%"))

        elif campo == "telefono":
            query = query.filter(Venta.telefono.ilike(f"%{q}%"))

        elif campo == "medio_pago":
            query = query.filter(Venta.medio_pago.ilike(f"%{q}%"))

        elif campo == "observaciones":
            query = query.filter(Venta.observaciones.ilike(f"%{q}%"))

        elif campo == "precio":
            query = query.filter(Venta.precio == q)

    if fecha:
        from datetime import datetime
        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
            query = query.filter(db.func.date(Venta.fecha) == fecha_dt)
        except:
            pass

    per_page = request.args.get("per_page", 10, type=int)

    ventas = query.order_by(Venta.fecha.desc()).paginate(
        page=page,
        per_page=per_page
    )

    return render_template(
        "ventas.html",
        ventas=ventas,
        trabajadoras=trabajadoras_activas(),
        servicios=Servicio.query.order_by(Servicio.nombre.asc()).all(),
        campo=campo,
        q=q,
        fecha=fecha,
        per_page=per_page
    )