from extensions import db

class Boleta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100))
    monto = db.Column(db.Float)
    fecha = db.Column(db.Date)


class Factura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100))
    monto = db.Column(db.Float)
    fecha = db.Column(db.Date)