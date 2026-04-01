def calcular_penalidad(dt_real, dt_oficial):
    """
    Regla de negocio:
    - 30 min de tolerancia
    - 1 sol por minuto adicional
    """

    minutos = int((dt_real - dt_oficial).total_seconds() / 60)

    tolerancia = 30
    costo_por_minuto = 1

    minutos_tarde = max(0, minutos - tolerancia)
    penalidad = minutos_tarde * costo_por_minuto

    return minutos_tarde, penalidad