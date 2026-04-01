from extensions import db


def obtener_kpis(fecha_inicio=None, fecha_fin=None, trabajadora_id=None):

    # imports locales
    from models import Venta, Trabajadora
    from sqlalchemy.orm import joinedload

    # ================= BASE: TODAS LAS TRABAJADORAS =================
    trabajadoras = Trabajadora.query.filter_by(activo=True).all()

    resumen = {t.nombre: 0 for t in trabajadoras}

    # ================= QUERY VENTAS =================
    query = Venta.query.options(joinedload(Venta.trabajadora))

    if fecha_inicio:
        query = query.filter(Venta.fecha >= fecha_inicio)

    if fecha_fin:
        query = query.filter(Venta.fecha <= fecha_fin)

    if trabajadora_id:
        query = query.filter(Venta.trabajadora_id == trabajadora_id)

    ventas = query.all()

    # ================= SUMAR VENTAS =================
    for v in ventas:
        nombre = v.trabajadora.nombre

        if nombre not in resumen:
            resumen[nombre] = 0  # 👈 evita KeyError (trabajadora inactiva)

        resumen[nombre] += v.precio
        
    # ================= TOTAL =================
    total = round(sum(resumen.values()), 2)

    # ================= COMISIONES =================
    comisiones = {}

    for t in trabajadoras:
        nombre = t.nombre
        total_v = resumen[nombre]

        com = 0

        if t.tipo_pago == "porcentaje":
            com = total_v * (t.comision / 100)

        elif t.tipo_pago == "meta":
            if total_v >= t.meta_2:
                com = total_v * (t.comision_meta_2 / 100)
            elif total_v >= t.meta_1:
                com = total_v * (t.comision_meta_1 / 100)

        comisiones[nombre] = round(com, 2)

    # ================= ORDENAR =================
    resumen_ordenado = dict(sorted(resumen.items(), key=lambda x: x[1], reverse=True))
    comisiones_ordenadas = dict(sorted(comisiones.items(), key=lambda x: x[1], reverse=True))

    ranking = list(resumen_ordenado.items())

    return {
        "total_general": total,
        "resumen": resumen_ordenado,
        "comisiones": comisiones_ordenadas,
        "ranking": ranking
    }