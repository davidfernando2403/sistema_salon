from flask import Blueprint, render_template, request, redirect, session
from models import Venta, Servicio, Trabajadora
from extensions import db
from utils.time import ahora_peru

from sqlalchemy import extract, func

graficos_bp = Blueprint("graficos", __name__)

@graficos_bp.route("/graficos")
def graficos():

    if "user_id" not in session:
        return redirect("/login")

    hoy = ahora_peru()

    mes_sel = request.args.get("mes") or f"{hoy.year}-{str(hoy.month).zfill(2)}"
    anio = int(mes_sel.split("-")[0])
    mes = int(mes_sel.split("-")[1])

    # ================= 1. VENTAS POR DIA =================
    ventas = db.session.query(
        extract("day", Venta.fecha),
        func.sum(Venta.precio)
    ).filter(
        extract("year", Venta.fecha)==anio,
        extract("month", Venta.fecha)==mes
    ).group_by(
        extract("day", Venta.fecha)
    ).order_by(
        extract("day", Venta.fecha)
    ).all()

    dias = [int(d) for d,_ in ventas]
    totales_dia = [float(t or 0) for _,t in ventas]

    # ================= 2. PRODUCCION POR TRABAJADORA =================
    produccion = db.session.query(
        extract("day", Venta.fecha),
        Trabajadora.nombre,
        func.sum(Venta.precio)
    ).join(Trabajadora).filter(
        extract("year", Venta.fecha)==anio,
        extract("month", Venta.fecha)==mes
    ).group_by(
        extract("day", Venta.fecha),
        Trabajadora.nombre
    ).all()

    prod_dict = {}

    for d,nombre,total in produccion:
        prod_dict.setdefault(nombre,{})
        prod_dict[nombre][int(d)] = float(total or 0)

    prod_labels = sorted({d for datos in prod_dict.values() for d in datos.keys()})

    prod_datasets = []

    for nombre,datos in prod_dict.items():
        fila = [datos.get(d,0) for d in prod_labels]

        prod_datasets.append({
            "label": nombre,
            "data": fila
        })

    # ================= 3. PRODUCCION MES A MES =================
    produccion_mes = db.session.query(
        extract("year",Venta.fecha),
        extract("month",Venta.fecha),
        func.sum(Venta.precio)
    ).group_by(
        extract("year",Venta.fecha),
        extract("month",Venta.fecha)
    ).order_by(
        extract("year",Venta.fecha),
        extract("month",Venta.fecha)
    ).all()

    meses_labels = [f"{int(y)}-{str(int(m)).zfill(2)}" for y,m,_ in produccion_mes]
    meses_totales = [float(t or 0) for _,_,t in produccion_mes]

    # ================= 4. SERVICIOS =================
    mes_serv = request.args.get("mes_servicios") or mes_sel
    orden = request.args.get("orden") or "cantidad"

    anio_serv = int(mes_serv.split("-")[0])
    mes_serv_num = int(mes_serv.split("-")[1])

    servicios = db.session.query(
        Servicio.nombre,
        func.count(Venta.id),
        func.sum(Venta.precio)
    ).join(Venta).filter(
        extract("year", Venta.fecha)==anio_serv,
        extract("month", Venta.fecha)==mes_serv_num
    ).group_by(Servicio.nombre).all()

    servicios = [
        {
            "nombre": s[0],
            "cantidad": int(s[1] or 0),
            "total": float(s[2] or 0)
        }
        for s in servicios
    ]

    if orden == "total":
        servicios.sort(key=lambda x: x["total"], reverse=True)
    else:
        servicios.sort(key=lambda x: x["cantidad"], reverse=True)

    serv_nombres = [s["nombre"] for s in servicios]
    serv_cantidad = [s["cantidad"] for s in servicios]
    serv_totales = [s["total"] for s in servicios]

    # ================= 5. MEDIOS DE PAGO =================
    mes_pagos = request.args.get("mes_pagos") or mes_sel

    anio_p = int(mes_pagos.split("-")[0])
    mes_p = int(mes_pagos.split("-")[1])

    pagos = db.session.query(
        func.lower(Venta.medio_pago),
        func.sum(Venta.precio)
    ).filter(
        extract("year",Venta.fecha)==anio_p,
        extract("month",Venta.fecha)==mes_p
    ).group_by(
        func.lower(Venta.medio_pago)
    ).all()

    pago_labels = [p[0].capitalize() for p in pagos]
    pago_totales = [float(p[1] or 0) for p in pagos]

    top_servicios = servicios[:10]

    return render_template(
        "graficos.html",
        mes_sel=mes_sel,
        dias=dias,
        totales_dia=totales_dia,
        prod_labels=prod_labels,
        prod_datasets=prod_datasets,
        meses_labels=meses_labels,
        meses_totales=meses_totales,
        serv_nombres=serv_nombres,
        serv_cantidad=serv_cantidad,
        serv_totales=serv_totales,
        pago_labels=pago_labels,
        pago_totales=pago_totales,
        orden=orden,
        mes_serv=mes_serv,
        servicios=servicios,
        top_servicios=top_servicios,
        mes_pagos=mes_pagos
    )