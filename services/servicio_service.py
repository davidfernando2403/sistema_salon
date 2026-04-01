from models import Servicio

def obtener_servicios():
    return Servicio.query.order_by(Servicio.nombre.asc()).all()