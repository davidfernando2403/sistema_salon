from extensions import db

from datetime import timedelta
import math

def trabajadoras_activas():
    from models import Trabajadora

    return Trabajadora.query.filter_by(activo=True)\
        .order_by(Trabajadora.nombre)\
        .all()

def servicios_ordenados():
    from models import Servicio

    return Servicio.query.order_by(Servicio.nombre.asc()).all()

def calcular_boleta(trabajadora, fecha_inicio, fecha_fin):

    from models import Venta, Asistencia
    from extensions import db
    from datetime import timedelta

    ventas = Venta.query.filter(
        Venta.trabajadora_id == trabajadora.id,
        db.func.date(Venta.fecha) >= fecha_inicio,
        db.func.date(Venta.fecha) <= fecha_fin
    ).all()

    total_ventas = sum(v.precio for v in ventas)

    asistencias = Asistencia.query.filter(
        Asistencia.trabajadora_id == trabajadora.id,
        Asistencia.fecha.between(fecha_inicio, fecha_fin)
    ).all()

    tardanzas = sum(a.penalidad for a in asistencias)

    dias_falta = 0
    d = fecha_inicio

    while d <= fecha_fin:
        if d.weekday() != 6:
            existe = Asistencia.query.filter_by(
                trabajadora_id=trabajadora.id,
                fecha=d
            ).first()

            if not existe:
                dias_falta += 1

        d += timedelta(days=1)

    sueldo_mensual = trabajadora.sueldo_base or 0
    valor_dia = sueldo_mensual / 30 if sueldo_mensual else 0
    faltas = dias_falta * valor_dia

    sueldo = 0

    if trabajadora.tipo_pago in ["fijo", "meta"]:
        sueldo = trabajadora.sueldo_base / 2

    comision = 0

    if trabajadora.tipo_pago == "porcentaje":
        comision = total_ventas * trabajadora.comision / 100

    if trabajadora.tipo_pago == "meta":
        if total_ventas >= trabajadora.meta_2:
            comision = total_ventas * trabajadora.comision_meta_2 / 100
        elif total_ventas >= trabajadora.meta_1:
            comision = total_ventas * trabajadora.comision_meta_1 / 100

    total = sueldo + comision - tardanzas - faltas

    return {
        "ventas": round(total_ventas,2),
        "sueldo": round(sueldo,2),
        "comision": round(comision,2),
        "tardanzas": round(tardanzas,2),
        "faltas": round(faltas,2),
        "bonos": 0,
        "adelantos": 0,
        "descuentos": 0,
        "total": round(total,2),
        "dias_falta": dias_falta 
    }