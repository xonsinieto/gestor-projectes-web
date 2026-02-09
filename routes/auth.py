"""
Blueprint d'autenticacio OAuth amb Microsoft (MSAL).
"""
import msal
from flask import Blueprint, redirect, render_template, request, session, url_for

import config_web

auth_bp = Blueprint("auth", __name__)


def _build_msal_app():
    return msal.ConfidentialClientApplication(
        config_web.AZURE_CLIENT_ID,
        authority=config_web.AZURE_AUTHORITY,
        client_credential=config_web.AZURE_CLIENT_SECRET,
    )


def get_access_token():
    """Retorna el token d'acces actual o None si cal re-autenticar."""
    return session.get("access_token")


@auth_bp.route("/login")
def login():
    """Inicia el flux OAuth: redirigeix a Microsoft login."""
    app = _build_msal_app()
    redirect_uri = url_for("auth.callback", _external=True)
    auth_url = app.get_authorization_request_url(
        config_web.AZURE_SCOPES,
        redirect_uri=redirect_uri,
    )
    return redirect(auth_url)


@auth_bp.route("/callback")
def callback():
    """Rep el codi d'autoritzacio de Microsoft i obte el token."""
    code = request.args.get("code")
    if not code:
        return redirect(url_for("views.index"))

    app = _build_msal_app()
    redirect_uri = url_for("auth.callback", _external=True)

    result = app.acquire_token_by_authorization_code(
        code,
        scopes=config_web.AZURE_SCOPES,
        redirect_uri=redirect_uri,
    )

    if "access_token" in result:
        # Comprovar llista blanca d'emails
        claims = result.get("id_token_claims", {})
        email = (
            claims.get("preferred_username", "")
            or claims.get("email", "")
        ).lower()

        if config_web.EMAILS_AUTORITZATS and email not in config_web.EMAILS_AUTORITZATS:
            return render_template("acces_denegat.html", email=email), 403

        # Guardem nomes el token i email (la cookie te limit de 4KB)
        session["access_token"] = result["access_token"]
        session["ms_email"] = email
        session.permanent = True  # Activa PERMANENT_SESSION_LIFETIME (12h)
        return redirect(url_for("auth.select_user"))

    return f"Error d'autenticacio: {result.get('error_description', 'Desconegut')}", 400


@auth_bp.route("/select-user")
def select_user():
    """Mostra la llista d'usuaris del JSON per triar qui es l'usuari."""
    token = get_access_token()
    if not token:
        return redirect(url_for("auth.login"))

    from services.graph_client import GraphClient
    from services.data_manager_web import DataManagerWeb

    graph = GraphClient(token)
    dm = DataManagerWeb(graph)

    try:
        dm.carregar()
        usuaris = dm.usuaris
    except Exception:
        usuaris = []

    return render_template("select_user.html", usuaris=usuaris)


@auth_bp.route("/select-user", methods=["POST"])
def select_user_post():
    """Guarda la seleccio d'usuari a la sessio."""
    nom = request.form.get("usuari", "").strip()
    if nom:
        session["usuari_actual"] = nom
        return redirect(url_for("views.index"))
    return redirect(url_for("auth.select_user"))


@auth_bp.route("/logout")
def logout():
    """Tanca la sessio."""
    session.clear()
    return redirect(url_for("views.index"))
