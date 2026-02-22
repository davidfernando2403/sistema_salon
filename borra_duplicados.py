from app import app, db, Venta
from sqlalchemy import func

with app.app_context():

    duplicados = db.session.query(
        Venta.cliente,
        Venta.precio,
        Venta.fecha,
        Venta.trabajadora_id,
        Venta.servicio_id,
        func.count(Venta.id)
    ).group_by(
        Venta.cliente,
        Venta.precio,
        Venta.fecha,
        Venta.trabajadora_id,
        Venta.servicio_id
    ).having(func.count(Venta.id) > 1).all()

    total_borradas = 0

    for d in duplicados:
        ventas = Venta.query.filter_by(
            cliente=d[0],
            precio=d[1],
            fecha=d[2],
            trabajadora_id=d[3],
            servicio_id=d[4]
        ).order_by(Venta.id.asc()).all()

        # dejamos 1, borramos el resto
        for v in ventas[1:]:
            db.session.delete(v)
            total_borradas += 1

    db.session.commit()

    print("✅ Ventas duplicadas eliminadas:", total_borradas)