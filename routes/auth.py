from flask import Blueprint, render_template, request, redirect, session
from models import Usuario

auth_bp = Blueprint("auth", __name__)

# ================= LOGIN =================

@auth_bp.route("/login", methods=["GET","POST"])
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


# ================= LOGOUT =================

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")