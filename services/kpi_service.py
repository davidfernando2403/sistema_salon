from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload
from extensions import db



def obtener_kpis(fecha_inicio=None, fecha_fin=None, trabajadora_id=None):

    # 🔥 IMPORTS LOCALES (rompe el ciclo)
    from app import Venta, Trabajadora

    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    query = Venta.query.options(joinedload(Venta.trabajadora))

    if fecha_inicio:
        query = query.filter(Venta.fecha >= fecha_inicio)

    if fecha_fin:
        query = query.filter(Venta.fecha <= fecha_fin)

    if trabajadora_id:
        query = query.filter(Venta.trabajadora_id == trabajadora_id)

    ventas = query.all()

    total = round(sum(v.precio for v in ventas), 2)

    resumen = {}
    for v in ventas:
        nombre = v.trabajadora.nombre
        resumen[nombre] = resumen.get(nombre, 0) + v.precio

    comisiones = {}

    for nombre, total_v in resumen.items():
        t = Trabajadora.query.filter_by(nombre=nombre).first()

        com = 0
        if t:
            if t.tipo_pago == "porcentaje":
                com = total_v * (t.comision / 100)
            elif t.tipo_pago == "meta":
                if total_v >= t.meta_2:
                    com = total_v * (t.comision_meta_2 / 100)
                elif total_v >= t.meta_1:
                    com = total_v * (t.comision_meta_1 / 100)

        comisiones[nombre] = round(com, 2)

    ranking = sorted(resumen.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_general": total,
        "resumen": resumen,
        "comisiones": comisiones,
        "ranking": ranking
    }