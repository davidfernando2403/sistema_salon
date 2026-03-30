from extensions import db

class Asistencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date)
    hora_ingreso = db.Column(db.Time)
    minutos_tarde = db.Column(db.Integer)
    penalidad = db.Column(db.Float)

    trabajadora_id = db.Column(db.Integer, db.ForeignKey('trabajadora.id'))
    trabajadora = db.relationship('Trabajadora')