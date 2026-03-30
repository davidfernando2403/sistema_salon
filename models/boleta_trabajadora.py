from extensions import db

class BoletaTrabajadora(db.Model):
    __tablename__ = "boleta_trabajadora"

    id = db.Column(db.Integer, primary_key=True)

    trabajadora_id = db.Column(db.Integer, db.ForeignKey('trabajadora.id'))
    trabajadora = db.relationship("Trabajadora")

    fecha_inicio = db.Column(db.Date)
    fecha_fin = db.Column(db.Date)

    sueldo_base = db.Column(db.Float, default=0)
    comisiones = db.Column(db.Float, default=0)
    bonos = db.Column(db.Float, default=0)

    tardanzas = db.Column(db.Float, default=0)
    faltas = db.Column(db.Float, default=0)
    adelantos = db.Column(db.Float, default=0)
    descuentos_manual = db.Column(db.Float, default=0)

    subtotal_ingresos = db.Column(db.Float, default=0)
    subtotal_descuentos = db.Column(db.Float, default=0)

    total_pagar = db.Column(db.Float, default=0)

    modificada_manual = db.Column(db.Boolean, default=False)

    creado = db.Column(db.DateTime)

    cerrada = db.Column(db.Boolean, default=False)
    fecha_cierre = db.Column(db.DateTime)