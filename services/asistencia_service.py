from models import ConfiguracionTardanza

def obtener_configuracion(fecha):

    config = (
        ConfiguracionTardanza.query
        .filter(
            ConfiguracionTardanza.fecha_inicio <= fecha,
            ConfiguracionTardanza.activo == True
        )
        .order_by(ConfiguracionTardanza.fecha_inicio.desc())
        .first()
    )

    return config


def calcular_penalidad(dt_real, dt_oficial):

    fecha = dt_real.date()

    config = obtener_configuracion(fecha)

    # fallback seguridad
    tolerancia = 30
    costo_por_minuto = 1

    if config:
        tolerancia = config.tolerancia
        costo_por_minuto = config.descuento_por_minuto

    minutos = int((dt_real - dt_oficial).total_seconds() / 60)

    minutos_tarde = max(0, minutos - tolerancia)

    penalidad = minutos_tarde * costo_por_minuto

    return minutos_tarde, penalidad