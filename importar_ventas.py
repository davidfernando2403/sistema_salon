from app import app, db, Venta, Trabajadora, Servicio
import pandas as pd

with app.app_context():

    df = pd.read_excel("ventas.xlsx")

    contador = 0

    for _, row in df.iterrows():

        # limpiamos textos
        nombre_trab = str(row["trabajadora"]).strip().upper()
        nombre_serv = str(row["servicio"]).strip().upper()

        trabajadora = Trabajadora.query.filter(
            db.func.upper(Trabajadora.nombre) == nombre_trab
        ).first()

        servicio = Servicio.query.filter(
            db.func.upper(Servicio.nombre) == nombre_serv
        ).first()

        if not trabajadora or not servicio:
            print("❌ Error fila:", row)
            continue

        nueva = Venta(
            fecha=row["fecha"],               # ya viene como datetime
            cliente=row["cliente"],
            precio=float(row["precio"]),
            medio_pago=row["medio_pago"],
            dni=None if pd.isna(row["dni"]) else str(row["dni"]),
            telefono=None if pd.isna(row["telefono"]) else str(row["telefono"]),
            observaciones=None if pd.isna(row["observaciones"]) else row["observaciones"],
            trabajadora_id=trabajadora.id,
            servicio_id=servicio.id
        )

        db.session.add(nueva)
        contador += 1

    db.session.commit()

    print(f"✅ {contador} ventas importadas correctamente")
