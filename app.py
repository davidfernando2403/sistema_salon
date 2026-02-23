from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import session, redirect, url_for
from flask import flash
from sqlalchemy import func
from datetime import date
from sqlalchemy import extract


app = Flask(__name__)
app.secret_key = "clave_secreta_123"
import os

db_url = os.environ.get("DATABASE_URL")

if not db_url:
    raise RuntimeError("DATABASE_URL no está definido en Railway")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
db = SQLAlchemy(app)


# -------- MODELOS --------

class Trabajadora(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))

    tipo_pago = db.Column(db.String(20))
    sueldo_base = db.Column(db.Float, default=0)

    comision = db.Column(db.Float, default=0)

    meta_1 = db.Column(db.Float, default=0)
    comision_meta_1 = db.Column(db.Float, default=0)

    meta_2 = db.Column(db.Float, default=0)
    comision_meta_2 = db.Column(db.Float, default=0)
    
        # 👇 NUEVO CAMPO
    activo = db.Column(db.Boolean, default=True)
    
    from datetime import time

    hora_semana = db.Column(db.Time, default=time(10,0))
    hora_sabado = db.Column(db.Time, default=time(10,0))
    
class BoletaTrabajadora(db.Model):
    __tablename__ = "boleta_trabajadora"

    id = db.Column(db.Integer, primary_key=True)

    trabajadora_id = db.Column(db.Integer, db.ForeignKey('trabajadora.id'))
    trabajadora = db.relationship("Trabajadora")

    fecha_inicio = db.Column(db.Date)
    fecha_fin = db.Column(db.Date)

    sueldo_base = db.Column(db.Float, default=0)
    comisiones = db.Column(db.Float, default=0)
    bonos = db.Column(db.Float, default=0)

    tardanzas = db.Column(db.Float, default=0)
    faltas = db.Column(db.Float, default=0)
    adelantos = db.Column(db.Float, default=0)
    descuentos_manual = db.Column(db.Float, default=0)

    subtotal_ingresos = db.Column(db.Float, default=0)
    subtotal_descuentos = db.Column(db.Float, default=0)

    total_pagar = db.Column(db.Float, default=0)

    creado = db.Column(db.DateTime)
    
    # 🔥 NUEVOS CAMPOS
    cerrada = db.Column(db.Boolean, default=False)
    fecha_cierre = db.Column(db.DateTime)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    rol = db.Column(db.String(20))  # admin o trabajador


class Servicio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.Column(db.String(100))
    precio = db.Column(db.Float)

    # NUEVOS CAMPOS
    medio_pago = db.Column(db.String(50), nullable=False)
    dni = db.Column(db.String(20), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    observaciones = db.Column(db.String(200), nullable=True)

    trabajadora_id = db.Column(db.Integer, db.ForeignKey('trabajadora.id'))
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicio.id'))

    trabajadora = db.relationship('Trabajadora')
    servicio = db.relationship('Servicio')

class Asistencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date)
    hora_ingreso = db.Column(db.Time)
    minutos_tarde = db.Column(db.Integer)
    penalidad = db.Column(db.Float)

    trabajadora_id = db.Column(db.Integer, db.ForeignKey('trabajadora.id'))
    trabajadora = db.relationship('Trabajadora')

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


def trabajadoras_activas():
    return Trabajadora.query.filter_by(activo=True).order_by(Trabajadora.nombre).all()

from datetime import date, timedelta
from sqlalchemy import extract
import math

def calcular_boleta(trabajadora, fecha_inicio, fecha_fin):

    # ================= VENTAS DEL PERIODO =================

    ventas = Venta.query.filter(
        Venta.trabajadora_id == trabajadora.id,
        Venta.fecha >= fecha_inicio,
        Venta.fecha <= fecha_fin
    ).all()

    total_ventas = sum(v.precio for v in ventas)

    # ================= ASISTENCIAS (TARDANZAS) =================

    asistencias = Asistencia.query.filter(
        Asistencia.trabajadora_id == trabajadora.id,
        Asistencia.fecha >= fecha_inicio,
        Asistencia.fecha <= fecha_fin
    ).all()

    tardanzas = sum(a.penalidad for a in asistencias)

# ================= FALTAS =================

    dias_falta = 0
    d = fecha_inicio

    while d <= fecha_fin:

        # ignorar domingos
        if d.weekday() != 6:

            existe = Asistencia.query.filter_by(
                trabajadora_id=trabajadora.id,
                fecha=d
            ).first()

            if not existe:
                dias_falta += 1

        d += timedelta(days=1)

    # calcular monto diario según sueldo mensual
    sueldo_mensual = trabajadora.sueldo_base or 0
    valor_dia = sueldo_mensual / 30 if sueldo_mensual else 0

    faltas = dias_falta * valor_dia

    # ================= SUELDO BASE =================

    sueldo = 0

    if trabajadora.tipo_pago in ["fijo", "meta"]:
        sueldo = trabajadora.sueldo_base / 2

    # ================= COMISIONES =================

    comision = 0

    if trabajadora.tipo_pago == "porcentaje":
        comision = total_ventas * trabajadora.comision / 100

    if trabajadora.tipo_pago == "meta":

        if total_ventas >= trabajadora.meta_2:
            comision = total_ventas * trabajadora.comision_meta_2 / 100

        elif total_ventas >= trabajadora.meta_1:
            comision = total_ventas * trabajadora.comision_meta_1 / 100

    # ================= TOTAL =================

    total = sueldo + comision - tardanzas - faltas

    return {
        "ventas": round(total_ventas,2),
        "sueldo": round(sueldo,2),
        "comision": round(comision,2),
        "tardanzas": round(tardanzas,2),
        "faltas": round(faltas,2),
        "bonos": 0,
        "adelantos": 0,
        "descuentos": 0,
        "total": round(total,2),
        "dias_falta": dias_falta 
    }

# -------- RUTAS --------

@app.route("/")
def index():

    if "user_id" not in session:
        return redirect("/login")

    ventas = Venta.query.all()
    trabajadoras = trabajadoras_activas()
    servicios = Servicio.query.all()

    return render_template(
        "index.html",
        ventas=ventas,
        trabajadoras=trabajadoras,
        servicios=servicios
    )

@app.route("/admin/trabajadoras", methods=["GET","POST"])
def admin_trabajadoras():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import datetime, time
    import math

    accion = request.form.get("accion")
    edit_id = request.args.get("edit")

    t_edit = Trabajadora.query.get(edit_id) if edit_id else None

    # ================= CREAR =================

    if request.method == "POST" and accion == "crear":

        nueva = Trabajadora(
            nombre=request.form["nombre"],
            tipo_pago=request.form["tipo_pago"],
            sueldo_base=float(request.form.get("sueldo_base") or 0),
            comision=float(request.form.get("comision") or 0),
            meta_1=float(request.form.get("meta_1") or 0),
            comision_meta_1=float(request.form.get("comision_meta_1") or 0),
            meta_2=float(request.form.get("meta_2") or 0),
            comision_meta_2=float(request.form.get("comision_meta_2") or 0),
            activo=True,
            hora_semana=time(10,0),
            hora_sabado=time(10,0)
        )

        db.session.add(nueva)
        db.session.commit()

        flash("Trabajadora creada ✅","success")
        return redirect("/admin/trabajadoras")

    # ================= EDITAR =================

    if request.method == "POST" and accion == "editar":

        t = Trabajadora.query.get(request.form["id"])

        t.nombre = request.form["nombre"]
        t.tipo_pago = request.form["tipo_pago"]
        t.sueldo_base = float(request.form.get("sueldo_base") or 0)
        t.comision = float(request.form.get("comision") or 0)

        t.meta_1 = float(request.form.get("meta_1") or 0)
        t.comision_meta_1 = float(request.form.get("comision_meta_1") or 0)

        t.meta_2 = float(request.form.get("meta_2") or 0)
        t.comision_meta_2 = float(request.form.get("comision_meta_2") or 0)

        t.activo = True if request.form.get("activo") else False

        hora_semana = request.form.get("hora_semana")
        hora_sabado = request.form.get("hora_sabado")

        if hora_semana:
            t.hora_semana = time.fromisoformat(hora_semana)

        if hora_sabado:
            t.hora_sabado = time.fromisoformat(hora_sabado)

        db.session.commit()

        # ===== RECALCULAR ASISTENCIAS =====

        asistencias = Asistencia.query.filter_by(trabajadora_id=t.id).all()

        for a in asistencias:

            fecha = a.fecha
            hora = a.hora_ingreso

            dia = fecha.weekday()

            if dia == 5:
                hora_oficial = t.hora_sabado
            else:
                hora_oficial = t.hora_semana

            dt_real = datetime.combine(fecha, hora)
            dt_oficial = datetime.combine(fecha, hora_oficial)

            minutos = int((dt_real - dt_oficial).total_seconds()/60)
            minutos_tarde = max(0, minutos - 10)

            bloques = math.ceil(minutos_tarde / 10) if minutos_tarde>0 else 0
            penalidad = bloques * 5

            a.minutos_tarde = minutos_tarde
            a.penalidad = penalidad

        db.session.commit()

        flash("Trabajadora actualizada y asistencias recalculadas ✅","success")
        return redirect("/admin/trabajadoras")

    lista = Trabajadora.query.order_by(Trabajadora.nombre).all()

    return render_template(
        "admin_trabajadoras.html",
        trabajadoras=lista,
        t_edit=t_edit
    )

from flask import flash, redirect, request

@app.route("/ventas/guardar", methods=["POST"])
def ventas_guardar():

    from datetime import datetime

    try:

        fecha_form = request.form.get("fecha")

        if fecha_form:
            fecha = datetime.strptime(fecha_form, "%Y-%m-%d")
        else:
            fecha = datetime.now()

        nueva = Venta(
            fecha=fecha,
            cliente=request.form['cliente'],
            precio=float(request.form['precio']),
            medio_pago=request.form['medio_pago'],
            dni=request.form.get('dni'),
            telefono=request.form.get('telefono'),
            observaciones=request.form.get('observaciones'),
            trabajadora_id=int(request.form['trabajadora']),
            servicio_id=int(request.form['servicio'])
        )

        db.session.add(nueva)
        db.session.commit()

        flash("Venta registrada correctamente ✅", "ventas")

    except Exception as e:
        db.session.rollback()
        flash("Error al registrar venta ❌", "danger")
        print(e)

    return redirect("/ventas/nueva")



@app.route("/ventas/nueva")
def ventas_nueva():

    from datetime import date

    hoy = date.today()

    ventas = Venta.query.filter(
        db.func.date(Venta.fecha)==hoy
    ).order_by(Venta.fecha.desc()).all()

    return render_template(
        "venta_nueva.html",
        ventas=ventas,
        trabajadoras=trabajadoras_activas(),
        servicios=Servicio.query.all()
    )

@app.route("/ventas/historial")
def ventas_historial():

    campo = request.args.get("campo")
    q = request.args.get("q")
    fecha = request.args.get("fecha")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    ventas = Venta.query

    from datetime import datetime

    if campo and q:

        if campo == "cliente":
            ventas = ventas.filter(Venta.cliente.ilike(f"%{q}%"))

        elif campo == "dni":
            ventas = ventas.filter(Venta.dni.ilike(f"%{q}%"))

        elif campo == "telefono":
            ventas = ventas.filter(Venta.telefono.ilike(f"%{q}%"))

        elif campo == "trabajadora":
            ventas = ventas.join(Trabajadora).filter(
                Trabajadora.nombre.ilike(f"%{q}%")
            )

        elif campo == "servicio":
            ventas = ventas.join(Servicio).filter(
                Servicio.nombre.ilike(f"%{q}%")
            )

    if fecha and fecha != "None":
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
        ventas = ventas.filter(db.func.date(Venta.fecha) == fecha_dt)

    from sqlalchemy import func

    total_ventas = ventas.with_entities(func.coalesce(func.sum(Venta.precio), 0)).scalar()
    cantidad = ventas.count()
    
    ventas = ventas.order_by(Venta.fecha.desc()).paginate(page=page, per_page=per_page)

    return render_template(
        "ventas_historial.html",
        ventas=ventas,
        campo=campo,
        q=q,
        fecha=fecha,
        per_page=per_page,
        total_ventas=total_ventas,
        cantidad=cantidad
    )

    
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        user = Usuario.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()

        if user:
            session["user_id"] = user.id
            session["rol"] = user.rol
            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/servicios")
def servicios():

    if session.get("rol") != "admin":
        return redirect("/")

    lista = Servicio.query.all()
    return render_template("servicios.html", servicios=lista)

@app.route("/servicios/agregar", methods=["POST"])
def agregar_servicio():

    if session.get("rol") != "admin":
        return redirect("/")

    nombre = request.form["nombre"]

    nuevo = Servicio(nombre=nombre)
    db.session.add(nuevo)
    db.session.commit()

    return redirect("/servicios")

@app.route("/servicios/editar/<int:id>", methods=["POST"])
def editar_servicio(id):

    if session.get("rol") != "admin":
        return redirect("/")

    servicio = Servicio.query.get(id)
    servicio.nombre = request.form["nombre"]

    db.session.commit()

    return redirect("/servicios")

@app.route("/servicios/eliminar/<int:id>")
def eliminar_servicio(id):

    if session.get("rol") != "admin":
        return redirect("/")

    servicio = Servicio.query.get(id)

    db.session.delete(servicio)
    db.session.commit()

    return redirect("/servicios")

@app.route("/ventas")
def ventas():

    if session.get("rol") != "admin":
        return redirect("/")

    page = request.args.get("page", 1, type=int)
    campo = request.args.get("campo")
    q = request.args.get("q")
    fecha = request.args.get("fecha")

    query = Venta.query

    if campo and q:

        if campo == "cliente":
            query = query.filter(Venta.cliente.ilike(f"%{q}%"))

        elif campo == "dni":
            query = query.filter(Venta.dni.ilike(f"%{q}%"))

        elif campo == "telefono":
            query = query.filter(Venta.telefono.ilike(f"%{q}%"))

        elif campo == "trabajadora":
            query = query.join(Trabajadora).filter(
                Trabajadora.nombre.ilike(f"%{q}%")
            )

        elif campo == "servicio":
            query = query.join(Servicio).filter(
                Servicio.nombre.ilike(f"%{q}%")
            )

    if fecha:
        from datetime import datetime
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
        query = query.filter(db.func.date(Venta.fecha)==fecha_dt)

    ventas = query.order_by(Venta.fecha.desc()).paginate(page=page, per_page=10)

    return render_template(
        "ventas.html",
        ventas=ventas,
        trabajadoras=trabajadoras_activas(),
        servicios=Servicio.query.all(),
        campo=campo,
        q=q,
        fecha=fecha
    )


@app.route("/ventas/editar/<int:id>", methods=["POST"])
def editar_venta(id):

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import datetime

    v = Venta.query.get_or_404(id)

    try:

        fecha_form = request.form.get("fecha")
        if fecha_form:
            v.fecha = datetime.strptime(fecha_form, "%Y-%m-%d")

        v.servicio_id = int(request.form["servicio"])
        v.trabajadora_id = int(request.form["trabajadora"])
        v.precio = float(request.form["precio"])

        v.cliente = request.form.get("cliente")
        v.medio_pago = request.form.get("medio_pago")
        v.dni = request.form.get("dni") or None
        v.telefono = request.form.get("telefono") or None
        v.observaciones = request.form.get("observaciones")

        db.session.commit()
        flash("Venta actualizada ✅", "success")

    except Exception as e:
        db.session.rollback()
        flash("Error al actualizar ❌", "danger")
        print(e)

    return redirect("/ventas")



@app.route("/ventas/eliminar/<int:id>")
def eliminar_venta(id):

    if session.get("rol") != "admin":
        return redirect("/")

    v = Venta.query.get(id)
    db.session.delete(v)
    db.session.commit()

    return redirect("/ventas")


@app.route('/comisiones')
def comisiones():
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")

    if not desde or not hasta:
        return "Usa ?desde=2026-01-01&hasta=2026-01-15"

    desde = datetime.strptime(desde, "%Y-%m-%d")
    hasta = datetime.strptime(hasta, "%Y-%m-%d")

    resultado = []

    trabajadoras = trabajadoras_activas()

    for t in trabajadoras:
        ventas = Venta.query.filter(
            Venta.trabajadora_id == t.id,
            Venta.fecha >= desde,
            Venta.fecha <= hasta
        ).all()

        total = sum(v.precio for v in ventas)

        comision_total = 0

        if t.tipo_pago == "porcentaje":
            comision_total = total * (t.comision / 100)

        elif t.tipo_pago == "meta":
            if total >= t.meta_2:
                comision_total = total * (t.comision_meta_2 / 100)
            elif total >= t.meta_1:
                comision_total = total * (t.comision_meta_1 / 100)

        pago = t.sueldo_base + comision_total

        resultado.append({
            "nombre": t.nombre,
            "ventas": total,
            "comision": comision_total,
            "pago": pago
        })

    return {"resultado": resultado}

from sqlalchemy import extract, func
from datetime import datetime


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    from datetime import datetime, timedelta
    from sqlalchemy import extract

    hoy = datetime.now()
    dia = hoy.day
    mes_actual = hoy.month
    anio_actual = hoy.year

    # ================= QUINCENA =================

    if dia <= 15:
        dia_inicio = 1
        dia_fin = 15
        titulo_quincena = "1–15"
    else:
        dia_inicio = 16
        dia_fin = 31
        titulo_quincena = "16–fin de mes"

    ventas_quincena = Venta.query.filter(
        extract("year", Venta.fecha)==anio_actual,
        extract("month", Venta.fecha)==mes_actual,
        extract("day", Venta.fecha)>=dia_inicio,
        extract("day", Venta.fecha)<=dia_fin
    ).all()

    resumen = {}
    for v in ventas_quincena:
        resumen[v.trabajadora.nombre] = resumen.get(v.trabajadora.nombre,0)+v.precio

    total_quincena = round(sum(resumen.values()),2)

    # ================= COMISIONES =================

    comisiones = {}

    for nombre,total in resumen.items():

        if nombre=="Avril":
            com = total*0.13 if total>=3000 else total*0.10 if total>=1500 else 0
        elif nombre=="Mariana":
            com = total*0.13 if total>=1700 else total*0.10 if total>=1000 else 0
        elif nombre=="Laurent":
            com = total*0.40
        elif nombre=="Maju":
            com = total*0.50
        else:
            com = 0

        comisiones[nombre]=round(com,2)

    ranking = sorted(resumen.items(), key=lambda x:x[1], reverse=True)

# ================= HOY =================

    from sqlalchemy import func
    from datetime import date

    hoy = date.today()

    # total vendido hoy
    ventas_hoy = Venta.query.filter(db.func.date(Venta.fecha)==hoy).all()
    total_hoy = round(sum(v.precio for v in ventas_hoy),2)

    # TODAS las trabajadoras
    trabajadoras_hoy = Trabajadora.query.filter_by(activo=True).order_by(Trabajadora.nombre).all()

    # ventas de hoy agrupadas
    ventas_por_trabajadora = dict(db.session.query(
        Trabajadora.id,
        func.coalesce(func.sum(Venta.precio),0)
    ).join(Venta)\
    .filter(db.func.date(Venta.fecha)==hoy, Trabajadora.activo==True)\
    .group_by(Trabajadora.id)\
    .all())

    # construir resumen completo (incluye ceros)
    resumen_hoy={}

    for t in trabajadoras_hoy:
        resumen_hoy[t.nombre]=float(ventas_por_trabajadora.get(t.id,0))
    # ================= MES ACTUAL =================

    ventas_mes_actual = Venta.query.filter(
        extract("year", Venta.fecha)==anio_actual,
        extract("month", Venta.fecha)==mes_actual
    ).all()

    total_mes_actual = round(sum(v.precio for v in ventas_mes_actual),2)

    meses = {
        1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
        7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
    }

    nombre_mes = meses[mes_actual]

    # ================= KPI BOLETAS MES ACTUAL =================

    boletas_mes_actual = Boleta.query.filter(
        extract("year", Boleta.fecha)==anio_actual,
        extract("month", Boleta.fecha)==mes_actual
    ).all()

    total_boletas_mes_actual = round(sum(b.monto for b in boletas_mes_actual),2)

    # ================= FILTRO RANGO =================

    desde=request.args.get("desde")
    hasta=request.args.get("hasta")
    total_rango=None

    if desde and hasta:
        d1=datetime.strptime(desde,"%Y-%m-%d")
        d2=datetime.strptime(hasta,"%Y-%m-%d")+timedelta(days=1)

        ventas=Venta.query.filter(Venta.fecha>=d1,Venta.fecha<d2).all()
        total_rango=round(sum(v.precio for v in ventas),2)

    # ================= MES SELECCIONADO =================

    mes_sel=request.args.get("mes")
    total_mes_seleccionado=None

    if mes_sel:
        a=int(mes_sel.split("-")[0])
        m=int(mes_sel.split("-")[1])

        ventas=Venta.query.filter(extract("year",Venta.fecha)==a,extract("month",Venta.fecha)==m).all()
        total_mes_seleccionado=round(sum(v.precio for v in ventas),2)

    # ================= BOLETAS / FACTURAS =================

    mes_boleta=request.args.get("mes_boleta") or f"{anio_actual}-{str(mes_actual).zfill(2)}"
    mes_factura=request.args.get("mes_factura") or f"{anio_actual}-{str(mes_actual).zfill(2)}"

    a,m=map(int,mes_boleta.split("-"))
    total_boletas_mes=round(sum(b.monto for b in Boleta.query.filter(extract("year",Boleta.fecha)==a,extract("month",Boleta.fecha)==m)),2)

    a,m=map(int,mes_factura.split("-"))
    total_facturas_mes=round(sum(f.monto for f in Factura.query.filter(extract("year",Factura.fecha)==a,extract("month",Factura.fecha)==m)),2)

    # ================= TOTAL DIA =================

    fecha_dia=request.args.get("dia")
    total_dia_seleccionado=None

    if fecha_dia:
        dt=datetime.strptime(fecha_dia,"%Y-%m-%d").date()
        ventas=Venta.query.filter(db.func.date(Venta.fecha)==dt).all()
        total_dia_seleccionado=round(sum(v.precio for v in ventas),2)

    # ================= PRODUCCION =================

    trab_sel=request.args.get("trabajadora_prod")
    desde_prod=request.args.get("desde_prod")
    hasta_prod=request.args.get("hasta_prod")

    total_produccion=None
    nombre_trabajadora_prod=None

    if trab_sel and desde_prod and hasta_prod:
        d1=datetime.strptime(desde_prod,"%Y-%m-%d")
        d2=datetime.strptime(hasta_prod,"%Y-%m-%d")

        ventas=Venta.query.filter(Venta.trabajadora_id==trab_sel,Venta.fecha>=d1,Venta.fecha<=d2).all()
        total_produccion=round(sum(v.precio for v in ventas),2)

        nombre_trabajadora_prod=Trabajadora.query.get(trab_sel).nombre

    return render_template(
        "dashboard.html",
        total_mes=total_quincena,
        resumen=resumen,
        comisiones=comisiones,
        ranking=ranking,
        titulo_quincena=titulo_quincena,
        total_hoy=total_hoy,
        resumen_hoy=resumen_hoy,
        total_rango=total_rango,
        total_mes_seleccionado=total_mes_seleccionado,
        desde=desde,
        hasta=hasta,
        mes_sel=mes_sel,
        total_boletas_mes=total_boletas_mes,
        total_facturas_mes=total_facturas_mes,
        mes_boleta=mes_boleta,
        mes_factura=mes_factura,
        total_mes_actual=total_mes_actual,
        nombre_mes=nombre_mes,
        fecha_dia=fecha_dia,
        total_dia_seleccionado=total_dia_seleccionado,
        trabajadoras=trabajadoras_activas(),
        total_produccion=total_produccion,
        nombre_trabajadora_prod=nombre_trabajadora_prod,
        desde_prod=desde_prod,
        hasta_prod=hasta_prod,
        total_boletas_mes_actual=total_boletas_mes_actual
    )


@app.route("/usuarios")
def usuarios():

    if session.get("rol") != "admin":
        return redirect("/")

    lista = Usuario.query.all()
    return render_template("usuarios.html", usuarios=lista)

@app.route("/usuarios/editar/<int:id>", methods=["POST"])
def editar_usuario(id):

    if session.get("rol") != "admin":
        return redirect("/")

    u = Usuario.query.get(id)

    u.username = request.form["username"]
    u.password = request.form["password"]

    db.session.commit()

    return redirect("/usuarios")

@app.route("/marcar", methods=["GET","POST"])
def marcar():

    from datetime import datetime
    import math

    trabajadoras = Trabajadora.query.filter_by(activo=True).order_by(Trabajadora.nombre).all()

    if request.method == "POST":

        trabajadora_id = int(request.form["trabajadora"])
        ahora = datetime.now()

        fecha = ahora.date()
        hora_ingreso = ahora.time()
        dia_semana = ahora.weekday()  # lunes=0
        
        # ===== DOMINGO LIBRE =====
        if dia_semana == 6:
            flash("Domingo es día libre ☀️","info")
            return redirect("/marcar")
        
        ya = Asistencia.query.filter_by(
            trabajadora_id=trabajadora_id,
            fecha=fecha
        ).first()

        if ya:
            flash("Ya marcaste hoy ❌","danger")
            return redirect("/marcar")

        t = Trabajadora.query.get(trabajadora_id)

        # ================= HORARIO DINAMICO =================

        if dia_semana == 5:   # sábado
            hora_oficial = t.hora_sabado
        else:
            hora_oficial = t.hora_semana

        # ================= CALCULO =================

        dt_real = datetime.combine(fecha, hora_ingreso)
        dt_oficial = datetime.combine(fecha, hora_oficial)

        minutos = int((dt_real - dt_oficial).total_seconds()/60)

        minutos_tarde = max(0, minutos - 10)

        bloques = math.ceil(minutos_tarde / 10) if minutos_tarde>0 else 0
        penalidad = bloques * 5

        nueva = Asistencia(
            fecha=fecha,
            hora_ingreso=hora_ingreso,
            minutos_tarde=minutos_tarde,
            penalidad=penalidad,
            trabajadora_id=trabajadora_id
        )

        db.session.add(nueva)
        db.session.commit()

        flash("Asistencia registrada ✅","success")
        return redirect("/marcar")

    return render_template("marcar.html", trabajadoras=trabajadoras)

@app.route("/asistencia_admin", methods=["GET","POST"])
def asistencia_admin():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import date, timedelta, datetime, time
    from sqlalchemy import extract
    import math

    accion = request.form.get("accion")
    edit_id = request.args.get("edit")

    # ================= EDITAR =================
    if request.method == "POST" and accion == "editar":

        a = Asistencia.query.get(request.form["id"])

        hora = request.form.get("hora")
        if hora:
            from datetime import datetime

            try:
                a.hora_ingreso = datetime.strptime(hora, "%H:%M").time()
            except:
                a.hora_ingreso = datetime.strptime(hora, "%H:%M:%S").time()

        # recalcular tardanza + penalidad automático
        trab = a.trabajadora

        if a.fecha.weekday() == 5:   # sábado
            hora_oficial = trab.hora_sabado
        else:
            hora_oficial = trab.hora_semana

        dt_real = datetime.combine(a.fecha, a.hora_ingreso)
        dt_oficial = datetime.combine(a.fecha, hora_oficial)

        minutos = int((dt_real - datetime.combine(a.fecha, hora_oficial)).total_seconds()/60)
        minutos_tarde = max(0, minutos - 10)

        bloques = math.ceil(minutos_tarde / 10) if minutos_tarde>0 else 0
        penalidad = bloques * 5

        a.minutos_tarde = minutos_tarde
        a.penalidad = penalidad

        db.session.commit()
        db.session.refresh(a)
        flash("Asistencia actualizada y penalidad recalculada ✅","success")
        return redirect("/asistencia_admin")

    # ================= BORRAR =================
    if request.method == "POST" and accion == "borrar":

        a = Asistencia.query.get(request.form["id"])
        db.session.delete(a)
        db.session.commit()

        flash("Asistencia eliminada 🗑","warning")
        return redirect("/asistencia_admin")

    # ================= MARCAR MANUAL =================
    if request.method == "POST" and accion == "manual":

        trabajadora_id = int(request.form["trabajadora"])
        fecha = datetime.strptime(request.form["fecha"],"%Y-%m-%d").date()

        # soporta HH:MM o HH:MM:SS
        hora = datetime.fromisoformat(f"2000-01-01 {request.form['hora']}").time()

        ya = Asistencia.query.filter_by(trabajadora_id=trabajadora_id, fecha=fecha).first()

        if not ya:

            t = Trabajadora.query.get(trabajadora_id)

            # ===== HORARIO DINAMICO =====
            if fecha.weekday() == 5:   # sábado
                hora_oficial = t.hora_sabado
            else:
                hora_oficial = t.hora_semana

            dt_real = datetime.combine(fecha, hora)
            dt_oficial = datetime.combine(fecha, hora_oficial)

            minutos = int((dt_real - dt_oficial).total_seconds()/60)
            minutos_tarde = max(0, minutos - 10)

            bloques = math.ceil(minutos_tarde / 10) if minutos_tarde>0 else 0
            penalidad = bloques * 5

            nueva = Asistencia(
                fecha=fecha,
                hora_ingreso=hora,
                minutos_tarde=minutos_tarde,
                penalidad=penalidad,
                trabajadora_id=trabajadora_id
            )

            db.session.add(nueva)
            db.session.commit()

            flash("Asistencia manual registrada ✅","success")

        return redirect("/asistencia_admin")

    # ================= LISTADO =================

    trabajadora_id = request.args.get("trabajadora")
    quincena = request.args.get("quincena")
    mes_sel = request.args.get("mes")

    trabajadoras = Trabajadora.query.filter_by(activo=True).order_by(Trabajadora.nombre).all()

    hoy = date.today()

    if mes_sel:
        anio, mes = map(int, mes_sel.split("-"))
    else:
        anio = hoy.year
        mes = hoy.month

    query = Asistencia.query.filter(
        extract('year', Asistencia.fecha)==anio,
        extract('month', Asistencia.fecha)==mes
    )

    if trabajadora_id:
        query = query.filter_by(trabajadora_id=trabajadora_id)

    registros = query.order_by(Asistencia.fecha.desc()).all()

    total_penalidad = sum(r.penalidad for r in registros)

    t_edit = Asistencia.query.get(edit_id) if edit_id else None
    
    # ================= DIAS SIN MARCAR =================

    from datetime import date

    faltas_tabla = {}

    hoy = date.today()

    # calcular rango según quincena
    if quincena == "1":
        inicio_q = date(anio, mes, 1)
        fin_q = date(anio, mes, 15)
    elif quincena == "2":
        inicio_q = date(anio, mes, 16)
        siguiente = date(anio + (mes==12), ((mes)%12)+1, 1)
        fin_q = siguiente - timedelta(days=1)
    else:
        inicio_q = date(anio, mes, 1)
        siguiente = date(anio + (mes==12), ((mes)%12)+1, 1)
        fin_q = siguiente - timedelta(days=1)

    # no mostrar fechas futuras
    fin_q = min(fin_q, hoy)

    fechas = []

    d = inicio_q
    while d <= fin_q:
        if d.weekday() != 6:
            fechas.append(d)
        d += timedelta(days=1)

    for f in fechas:
        faltas_tabla[f] = {}

        for t in trabajadoras:

            existe = Asistencia.query.filter_by(
                trabajadora_id=t.id,
                fecha=f
            ).first()

            faltas_tabla[f][t.nombre] = False if existe else True
            
    return render_template(
        "asistencia_admin.html",
        registros=registros,
        trabajadoras=trabajadoras,
        total_penalidad=total_penalidad,
        trabajadora_id=trabajadora_id,
        quincena=quincena,
        mes_sel=mes_sel,
        t_edit=t_edit,
        faltas_tabla=faltas_tabla,
        fechas=faltas_tabla.keys(),
    )

@app.route("/comprobantes", methods=["GET","POST"])
def comprobantes():

    from datetime import datetime

    if request.method == "POST":

        tipo = request.form["tipo"]
        codigo = request.form["codigo"]
        monto = float(request.form["monto"])
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()

        if tipo == "boleta":
            db.session.add(Boleta(codigo=codigo,monto=monto,fecha=fecha))

        else:
            db.session.add(Factura(codigo=codigo,monto=monto,fecha=fecha))

        db.session.commit()

        flash("Registrado correctamente ✅","success")

    boletas = Boleta.query.order_by(Boleta.fecha.desc()).all()
    facturas = Factura.query.order_by(Factura.fecha.desc()).all()

    return render_template("comprobantes.html", boletas=boletas, facturas=facturas)

@app.route("/graficos")
def graficos():

    if "user_id" not in session:
        return redirect("/login")

    from datetime import datetime
    from sqlalchemy import extract, func

    hoy = datetime.now()

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
        func.count(Venta.id).label("cantidad"),
        func.sum(Venta.precio).label("total")
    ).join(Venta).filter(
        extract("year", Venta.fecha)==anio_serv,
        extract("month", Venta.fecha)==mes_serv_num
    ).group_by(Servicio.nombre).all()

    # Convertir a lista manejable
    servicios = [
        {
            "nombre": s[0],
            "cantidad": int(s[1] or 0),
            "total": float(s[2] or 0)
        }
        for s in servicios
    ]

    # Orden dinámico
    if orden == "total":
        servicios.sort(key=lambda x: x["total"], reverse=True)
    else:
        servicios.sort(key=lambda x: x["cantidad"], reverse=True)

    serv_nombres = [s["nombre"] for s in servicios]
    serv_cantidad = [s["cantidad"] for s in servicios]
    serv_totales = [s["total"] for s in servicios]

# ================= 5. METODO DE PAGO =================

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
        
        mes_pagos=mes_pagos
    )

@app.route("/admin/recalcular_comisiones", methods=["POST"])
def preview_recalculo():

    from datetime import datetime
    import math

    if session.get("rol") != "admin":
        return redirect("/")

    desde = request.form["desde"]
    desde_dt = datetime.strptime(desde,"%Y-%m-%d")

    ventas = Venta.query.filter(Venta.fecha >= desde_dt).all()

    cambios = []

    for v in ventas:

        t = v.trabajadora
        total = v.precio

        comision = 0

        if t.tipo_pago == "porcentaje":
            comision = total * (t.comision/100)

        elif t.tipo_pago == "meta":

            if total >= t.meta_2:
                comision = total * (t.comision_meta_2/100)

            elif total >= t.meta_1:
                comision = total * (t.comision_meta_1/100)

        cambios.append({
            "venta": v.id,
            "trabajadora": t.nombre,
            "fecha": v.fecha.date(),
            "precio": total,
            "nueva_comision": round(comision,2)
        })

    return render_template(
        "preview_recalculo.html",
        cambios=cambios,
        desde=desde
    )

@app.route("/admin/aplicar_recalculo", methods=["POST"])
def aplicar_recalculo():

    from datetime import datetime

    if session.get("rol") != "admin":
        return redirect("/")

    desde = request.form["desde"]
    desde_dt = datetime.strptime(desde,"%Y-%m-%d")

    ventas = Venta.query.filter(Venta.fecha >= desde_dt).all()

    for v in ventas:

        t = v.trabajadora
        total = v.precio
        comision = 0

        if t.tipo_pago == "porcentaje":
            comision = total * (t.comision/100)

        elif t.tipo_pago == "meta":

            if total >= t.meta_2:
                comision = total * (t.comision_meta_2/100)

            elif total >= t.meta_1:
                comision = total * (t.comision_meta_1/100)

        v.comision = round(comision,2)

    db.session.commit()

    flash("Recalculo aplicado correctamente ✅","success")

    return redirect("/admin/trabajadoras")

@app.route("/boleta_trabajadora", methods=["GET","POST"])
def boleta_trabajadora():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import date, timedelta

    hoy = date.today()

    # ===== PERIODO QUINCENAL =====
    if hoy.day <= 15:
        inicio = date(hoy.year, hoy.month, 1)
        fin = date(hoy.year, hoy.month, 15)
        titulo = "1–15"
    else:
        inicio = date(hoy.year, hoy.month, 16)
        siguiente = date(hoy.year + (hoy.month==12), ((hoy.month)%12)+1, 1)
        fin = siguiente - timedelta(days=1)
        titulo = "16–fin"

    if fin.weekday() == 6:
        fin -= timedelta(days=1)

    trabajadoras = Trabajadora.query.filter_by(activo=True).all()

    edit_id = request.args.get("edit")
    edit_id = int(edit_id) if edit_id else None

    ver_id = request.args.get("ver")
    ver_id = int(ver_id) if ver_id else None

    hist = request.args.get("hist")

    filas = []

    # ===== ARMAR BOLETAS =====
    for t in trabajadoras:

        r = calcular_boleta(t, inicio, fin)

        # sueldo quincenal por defecto
        r["sueldo"] = round((t.sueldo_base or 0) / 2, 2)

        # 🔹 Asegurar separación de penalidades
        r["tardanzas"] = r.get("tardanzas", 0)
        r["faltas"] = r.get("faltas", 0)

        boleta = BoletaTrabajadora.query.filter_by(
            trabajadora_id=t.id,
            fecha_inicio=inicio,
            fecha_fin=fin
        ).first()

        # 🔒 bloqueo si está cerrada
        r["bloqueada"] = True if (boleta and boleta.cerrada) else False

        if boleta:
            r["sueldo"] = boleta.sueldo_base
            r["comision"] = boleta.comisiones
            r["bonos"] = boleta.bonos
            r["adelantos"] = boleta.adelantos
            r["descuentos"] = boleta.descuentos_manual

            # solo usar valores guardados si existen
            if boleta.tardanzas:
                r["tardanzas"] = boleta.tardanzas
            if boleta.faltas:
                r["faltas"] = boleta.faltas

        ingresos = r["sueldo"] + r["comision"] + r["bonos"]
        egresos = r["tardanzas"] + r["faltas"] + r["adelantos"] + r["descuentos"]

        r["total"] = ingresos - egresos

        filas.append({
            "id": t.id,
            "nombre": t.nombre,
            **r
        })

    # ===== FILTRAR SOLO LA SELECCIONADA =====
    if ver_id:
        filas = [f for f in filas if f["id"] == ver_id]

    # ===== GUARDAR EDICION =====
    if request.method == "POST":

        tid = int(request.form["trabajadora_id"])

        sueldo = float(request.form.get("sueldo") or 0)
        comision = float(request.form.get("comision") or 0)
        bonos = float(request.form.get("bonos") or 0)
        adelantos = float(request.form.get("adelantos") or 0)
        descuentos = float(request.form.get("descuentos") or 0)

        # 🔹 recalcular penalidades separadas
        r_calc = calcular_boleta(Trabajadora.query.get(tid), inicio, fin)
        tardanzas = r_calc.get("tardanzas", 0)
        faltas = r_calc.get("faltas", 0)

        ingresos = sueldo + comision + bonos
        egresos = tardanzas + faltas + adelantos + descuentos
        total = ingresos - egresos

        boleta = BoletaTrabajadora.query.filter_by(
            trabajadora_id=tid,
            fecha_inicio=inicio,
            fecha_fin=fin
        ).first()

        if not boleta:
            boleta = BoletaTrabajadora(
                trabajadora_id=tid,
                fecha_inicio=inicio,
                fecha_fin=fin
            )

        boleta.sueldo_base = sueldo
        boleta.comisiones = comision
        boleta.bonos = bonos
        boleta.adelantos = adelantos
        boleta.descuentos_manual = descuentos
        boleta.tardanzas = tardanzas
        boleta.faltas = faltas
        boleta.subtotal_ingresos = ingresos
        boleta.subtotal_descuentos = egresos
        boleta.total_pagar = total

        db.session.add(boleta)
        db.session.commit()

        flash("Boleta actualizada ✅","success")
        return redirect(f"/boleta_trabajadora?ver={tid}")

    historicos = []

    if hist:
        historicos = BoletaTrabajadora.query.filter_by(cerrada=True)\
            .order_by(BoletaTrabajadora.fecha_inicio.desc())\
            .all()

    return render_template(
        "boleta_trabajadora.html",
        filas=filas,
        todas_trabajadoras=trabajadoras,
        inicio=inicio,
        fin=fin,
        titulo=titulo,
        edit_id=edit_id,
        ver_id=ver_id,
        historicos=historicos,
        hist=hist
    )

@app.route("/cerrar_quincena")
def cerrar_quincena():

    if session.get("rol") != "admin":
        return redirect("/")

    from datetime import datetime, date, timedelta

    hoy = date.today()

    if hoy.day <= 15:
        inicio = date(hoy.year, hoy.month, 1)
        fin = date(hoy.year, hoy.month, 15)
    else:
        inicio = date(hoy.year, hoy.month, 16)
        siguiente = date(hoy.year + (hoy.month==12), ((hoy.month)%12)+1, 1)
        fin = siguiente - timedelta(days=1)

    boletas = BoletaTrabajadora.query.filter_by(
        fecha_inicio=inicio,
        fecha_fin=fin
    ).all()

    for b in boletas:
        b.cerrada = True
        b.fecha_cierre = datetime.now()

    db.session.commit()

    flash("Quincena cerrada. Boletas marcadas como pagadas 🔒","success")
    return redirect("/boleta_trabajadora")

@app.route("/boleta_pdf/<int:trabajadora_id>")
def boleta_pdf(trabajadora_id):

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from flask import send_file
    import io

    b = BoletaTrabajadora.query.filter_by(trabajadora_id=trabajadora_id)\
        .order_by(BoletaTrabajadora.id.desc()).first()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    y = 800
    c.drawString(50, y, "BOLETA DE PAGO"); y-=30
    c.drawString(50, y, f"Trabajadora: {b.trabajadora.nombre}"); y-=25
    c.drawString(50, y, f"Periodo: {b.fecha_inicio} - {b.fecha_fin}"); y-=30

    c.drawString(50, y, f"Sueldo: S/ {b.sueldo_base}"); y-=20
    c.drawString(50, y, f"Comisión: S/ {b.comisiones}"); y-=20
    c.drawString(50, y, f"Bonos: S/ {b.bonos}"); y-=20

    # 🔥 NUEVO
    c.drawString(50, y, f"Tardanzas: S/ {b.tardanzas}"); y-=20
    c.drawString(50, y, f"Faltas: S/ {b.faltas}"); y-=20

    c.drawString(50, y, f"Adelantos: S/ {b.adelantos}"); y-=20
    c.drawString(50, y, f"Descuentos: S/ {b.descuentos_manual}"); y-=30

    c.drawString(50, y, f"TOTAL A PAGAR: S/ {b.total_pagar}")

    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(buffer, download_name="boleta.pdf", mimetype="application/pdf")

