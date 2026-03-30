from flask import Blueprint, render_template, request, redirect, session
from models import Usuario
from extensions import db

usuarios_bp = Blueprint("usuarios", __name__)

## ================= LISTADO =================

@usuarios_bp.route("/usuarios")
def usuarios():

    if session.get("rol") != "admin":
        return redirect("/")

    lista = Usuario.query.all()

    return render_template("usuarios.html", usuarios=lista)

## ================= EDITAR  =================

@usuarios_bp.route("/usuarios/editar/<int:id>", methods=["POST"])
def editar_usuario(id):

    if session.get("rol") != "admin":
        return redirect("/")

    u = Usuario.query.get(id)

    u.username = request.form["username"]
    u.password = request.form["password"]

    db.session.commit()

    return redirect("/usuarios")