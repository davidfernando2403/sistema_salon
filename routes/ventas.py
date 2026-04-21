from datetime import datetime, time

from flask import Blueprint, render_template, request, redirect, session, flash
from models import Venta, Servicio
from extensions import db
from utils.time import ahora_peru, hoy_peru
from services.core_service import trabajadoras_activas
from models.caja_movimiento import CajaMovimiento
from sqlalchemy import func

ventas_bp = Blueprint("ventas", __name__)

# ================= NUEVA VENTA =================

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

# ================= GUARDAR VENTA =================
    
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
        db.session.flush()  # 👈 genera el ID sin hacer commit

        # ================= CAJA AUTOMÁTICA =================
        if nueva.medio_pago and nueva.medio_pago.strip().lower() == "efectivo":
            movimiento = CajaMovimiento(
                tipo="ingreso",
                monto=nueva.precio,
                detalle=f"Venta #{nueva.id}",
                origen="venta",
                venta_id=nueva.id
            )
            db.session.add(movimiento)

        db.session.commit()

        flash("Venta registrada correctamente ✅", "ventas")

    except Exception as e:
        db.session.rollback()
        flash("Error al registrar venta ❌", "danger")
        print(e)

    return redirect("/ventas/nueva")

# ================= LISTADO VENTAS =================

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

# ================= EDITAR VENTA =================
    
@ventas_bp.route("/ventas/editar/<int:id>", methods=["POST"])
def editar_venta(id):

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import datetime

    v = Venta.query.get_or_404(id)

    try:
        fecha_form = request.form.get("fecha")

        if fecha_form:
            v.fecha = datetime.strptime(fecha_form, "%Y-%m-%d")

        v.servicio_id = int(request.form["servicio"])
        v.trabajadora_id = int(request.form["trabajadora"])
        v.precio = float(request.form["precio"])

        v.cliente = request.form.get("cliente")
        v.medio_pago = request.form.get("medio_pago")
        v.dni = request.form.get("dni") or None
        v.telefono = request.form.get("telefono") or None
        v.observaciones = request.form.get("observaciones")

        db.session.commit()
        flash("Venta actualizada ✅", "success")

    except Exception as e:
        db.session.rollback()
        flash("Error al actualizar ❌", "danger")
        print(e)

    return redirect("/ventas")

@ventas_bp.route("/ventas/eliminar/<int:id>")
def eliminar_venta(id):

    if session.get("rol") != "admin":
        return redirect("/")

    v = Venta.query.get(id)

    db.session.delete(v)
    db.session.commit()

    return redirect("/ventas")

# ================= HISTORIAL VENTAS =================

@ventas_bp.route("/ventas/historial")
def ventas_historial():

    campo = request.args.get("campo")
    q = request.args.get("q")
    fecha = request.args.get("fecha")
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    ventas = Venta.query

    from datetime import datetime

    if campo and q:

        if campo == "cliente":
            ventas = ventas.filter(Venta.cliente.ilike(f"%{q}%"))

        elif campo == "dni":
            ventas = ventas.filter(Venta.dni.ilike(f"%{q}%"))

        elif campo == "telefono":
            ventas = ventas.filter(Venta.telefono.ilike(f"%{q}%"))

        elif campo == "medio_pago":
            ventas = ventas.filter(Venta.medio_pago.ilike(f"%{q}%"))

        elif campo == "observaciones":
            ventas = ventas.filter(Venta.observaciones.ilike(f"%{q}%"))

        elif campo == "precio":
            ventas = ventas.filter(Venta.precio == q)

        elif campo == "trabajadora":
            from models import Trabajadora
            ventas = ventas.join(Trabajadora).filter(
                Trabajadora.nombre.ilike(f"%{q}%")
            )

        elif campo == "servicio":
            ventas = ventas.join(Servicio).filter(
                Servicio.nombre.ilike(f"%{q}%")
            )

    # ================= FILTRO FECHAS =================

    if fecha and fecha != "None":
        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
            ventas = ventas.filter(func.date(Venta.fecha) == fecha_dt)
        except:
            pass

    elif fecha_inicio and fecha_fin and fecha_inicio != "None" and fecha_fin != "None":
        try:
            fi = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            ff = datetime.strptime(fecha_fin, "%Y-%m-%d")
            ff = datetime.combine(ff, time.max)

            ventas = ventas.filter(
                Venta.fecha >= fi,
                Venta.fecha <= ff
            )
        except:
            pass

    total_ventas = ventas.with_entities(
        func.coalesce(func.sum(Venta.precio), 0)
    ).scalar()

    cantidad = ventas.count()

    ventas = ventas.order_by(Venta.fecha.desc()).paginate(
        page=page,
        per_page=per_page
    )

    return render_template(
        "ventas_historial.html",
        ventas=ventas,
        campo=campo,
        q=q,
        fecha=fecha,
        per_page=per_page,
        total_ventas=total_ventas,
        cantidad=cantidad,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )

# ================= EXPORTAR EXCEL =================

@ventas_bp.route("/ventas/exportar")
def exportar_excel():

    from flask import request, send_file
    import pandas as pd
    import io
    from datetime import datetime

    ventas = Venta.query

    campo = request.args.get("campo")
    q = request.args.get("q")
    fecha = request.args.get("fecha")
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    # ================= FILTROS (MISMO QUE HISTORIAL) =================

    if campo and q:

        if campo == "cliente":
            ventas = ventas.filter(Venta.cliente.ilike(f"%{q}%"))

        elif campo == "trabajadora":
            from models import Trabajadora
            ventas = ventas.join(Trabajadora).filter(
                Trabajadora.nombre.ilike(f"%{q}%")
            )

        elif campo == "servicio":
            ventas = ventas.join(Servicio).filter(
                Servicio.nombre.ilike(f"%{q}%")
            )

    if fecha and fecha != "None":
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
        ventas = ventas.filter(func.date(Venta.fecha) == fecha_dt)

    elif fecha_inicio and fecha_fin:
        fi = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        ff = datetime.strptime(fecha_fin, "%Y-%m-%d")
        
        ff = datetime.combine(ff, time.max)

        ventas = ventas.filter(Venta.fecha >= fi, Venta.fecha <= ff)

    ventas = ventas.order_by(Venta.fecha.desc()).all()

    # ================= DATA =================

    data = []

    for v in ventas:
        data.append({
            "Fecha": v.fecha.strftime("%d/%m/%Y"),
            "Servicio": v.servicio.nombre if v.servicio else "",
            "Cliente": v.cliente,
            "Precio": v.precio,
            "Trabajadora": v.trabajadora.nombre if v.trabajadora else "",
            "Pago": v.medio_pago,
            "DNI": v.dni,
            "Telefono": v.telefono,
            "Observaciones": v.observaciones
        })

    df = pd.DataFrame(data)

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        download_name="ventas_filtradas.xlsx",
        as_attachment=True
    )