def obtener_ventas_hoy(hoy_date):

    from app import Venta, Trabajadora
    from extensions import db
    from sqlalchemy import func

    ventas_hoy = db.session.query(
        Trabajadora.nombre,
        func.coalesce(func.sum(Venta.precio), 0)
    ).outerjoin(
        Venta,
        (Venta.trabajadora_id == Trabajadora.id) &
        (db.func.date(Venta.fecha) == hoy_date)
    ).filter(
        Trabajadora.activo == True
    ).group_by(
        Trabajadora.nombre
    ).all()

    resumen_hoy = {nombre: float(total) for nombre, total in ventas_hoy}

    # 🔥 ordenado (como ya hiciste)
    resumen_hoy = dict(sorted(resumen_hoy.items(), key=lambda x: x[1], reverse=True))

    total_hoy = sum(resumen_hoy.values())

    return resumen_hoy, total_hoy