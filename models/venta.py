from extensions import db
from utils.time import ahora_peru

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=ahora_peru)

    cliente = db.Column(db.String(100))
    precio = db.Column(db.Float)

    medio_pago = db.Column(db.String(50), nullable=False)
    dni = db.Column(db.String(20), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    observaciones = db.Column(db.String(200), nullable=True)

    trabajadora_id = db.Column(db.Integer, db.ForeignKey('trabajadora.id'))
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicio.id'))

    trabajadora = db.relationship('Trabajadora')
    servicio = db.relationship('Servicio')