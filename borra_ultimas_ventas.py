from app import app, db, Venta

CANTIDAD = 249   # 👈 EXACTAMENTE tu Excel

with app.app_context():

    ultimas = Venta.query.order_by(Venta.id.desc()).limit(CANTIDAD).all()

    ids = [v.id for v in ultimas]

    borradas = Venta.query.filter(Venta.id.in_(ids)).delete(synchronize_session=False)

    db.session.commit()

    print("✅ Ventas eliminadas:", borradas)