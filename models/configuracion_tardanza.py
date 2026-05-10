from extensions import db

class ConfiguracionTardanza(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    fecha_inicio = db.Column(db.Date, nullable=False)

    tolerancia = db.Column(db.Integer, default=30)

    descuento_por_minuto = db.Column(db.Float, default=1)

    activo = db.Column(db.Boolean, default=True)