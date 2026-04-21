from datetime import datetime
from extensions import db

class CajaMovimiento(db.Model):
    __tablename__ = "caja_movimiento"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    tipo = db.Column(db.String(10))  # ingreso / egreso
    monto = db.Column(db.Float)

    detalle = db.Column(db.String(255))

    origen = db.Column(db.String(20))  # venta / manual
    venta_id = db.Column(db.Integer, nullable=True)