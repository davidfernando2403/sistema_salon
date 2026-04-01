from models import Venta

def obtener_ventas():
    return Venta.query.all()