"""
Blueprint de vistes HTML.
"""
from flask import Blueprint, redirect, render_template, session, url_for

from routes.auth import get_access_token

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Vista principal — dashboard o redirect a login."""
    token = get_access_token()
    if not token:
        return redirect(url_for("auth.login"))

    usuari = session.get("usuari_actual")
    if not usuari:
        return redirect(url_for("auth.select_user"))

    return render_template("dashboard.html", usuari_actual=usuari)
