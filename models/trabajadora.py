from extensions import db
from datetime import time

class Trabajadora(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))

    tipo_pago = db.Column(db.String(20))
    sueldo_base = db.Column(db.Float, default=0)

    comision = db.Column(db.Float, default=0)

    meta_1 = db.Column(db.Float, default=0)
    comision_meta_1 = db.Column(db.Float, default=0)

    meta_2 = db.Column(db.Float, default=0)
    comision_meta_2 = db.Column(db.Float, default=0)

    activo = db.Column(db.Boolean, default=True)

    hora_semana = db.Column(db.Time, default=time(10,0))
    hora_sabado = db.Column(db.Time, default=time(10,0))