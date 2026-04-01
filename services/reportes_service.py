def obtener_filtros_reportes(data):

    from models import Venta, Trabajadora
    from extensions import db
    from datetime import datetime, timedelta
    from sqlalchemy import extract

    desde = data.get("desde")
    hasta = data.get("hasta")
    mes_sel = data.get("mes")
    fecha_dia = data.get("dia")

    trab_sel = data.get("trabajadora_prod")
    desde_prod = data.get("desde_prod")
    hasta_prod = data.get("hasta_prod")

    total_rango = None
    total_mes_seleccionado = None
    total_dia_seleccionado = None
    total_produccion = None
    nombre_trabajadora_prod = None

    # ================= RANGO =================
    if desde and hasta:
        d1 = datetime.strptime(desde,"%Y-%m-%d")
        d2 = datetime.strptime(hasta,"%Y-%m-%d") + timedelta(days=1)

        total_rango = db.session.query(
            db.func.coalesce(db.func.sum(Venta.precio), 0)
        ).filter(
            Venta.fecha >= d1,
            Venta.fecha < d2
        ).scalar()

    # ================= MES =================
    if mes_sel:
        a, m = map(int, mes_sel.split("-"))

        total_mes_seleccionado = db.session.query(
            db.func.coalesce(db.func.sum(Venta.precio), 0)
        ).filter(
            extract("year",Venta.fecha)==a,
            extract("month",Venta.fecha)==m
        ).scalar()

    # ================= DIA =================
    if fecha_dia:
        dt = datetime.strptime(fecha_dia,"%Y-%m-%d").date()

        total_dia_seleccionado = db.session.query(
            db.func.coalesce(db.func.sum(Venta.precio), 0)
        ).filter(
            db.func.date(Venta.fecha)==dt
        ).scalar()

    # ================= PRODUCCION =================
    if trab_sel and desde_prod and hasta_prod:
        d1 = datetime.strptime(desde_prod,"%Y-%m-%d")
        d2 = datetime.strptime(hasta_prod,"%Y-%m-%d") + timedelta(days=1)

        total_produccion = db.session.query(
            db.func.coalesce(db.func.sum(Venta.precio), 0)
        ).filter(
            Venta.trabajadora_id==trab_sel,
            Venta.fecha>=d1,
            Venta.fecha<d2
        ).scalar()

        t = Trabajadora.query.get(trab_sel)
        nombre_trabajadora_prod = t.nombre if t else None

    return {
        "total_rango": round(total_rango,2) if total_rango else None,
        "total_mes_seleccionado": round(total_mes_seleccionado,2) if total_mes_seleccionado else None,
        "total_dia_seleccionado": round(total_dia_seleccionado,2) if total_dia_seleccionado else None,
        "total_produccion": round(total_produccion,2) if total_produccion else None,
        "nombre_trabajadora_prod": nombre_trabajadora_prod,

        # mantener filtros
        "desde": desde,
        "hasta": hasta,
        "mes_sel": mes_sel,
        "fecha_dia": fecha_dia,
        "trabajadora_prod": trab_sel,
        "desde_prod": desde_prod,
        "hasta_prod": hasta_prod,
    }