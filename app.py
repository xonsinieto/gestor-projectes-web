"""
Gestor de Projectes — Versio Web (Flask).
Punt d'entrada principal.
"""
from datetime import timedelta

from flask import Flask

import config_web


def create_app():
    app = Flask(__name__)
    app.secret_key = config_web.SECRET_KEY

    # --- Seguretat de la sessio ---
    app.config.update(
        SESSION_COOKIE_SECURE=True,       # Nomes HTTPS
        SESSION_COOKIE_HTTPONLY=True,      # No accessible des de JavaScript
        SESSION_COOKIE_SAMESITE="Lax",    # Proteccio CSRF basica
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),  # Sessio dura 12h
    )

    # Passar constants als templates Jinja2
    app.jinja_env.globals.update(
        ESTATS=config_web.ESTATS,
        ETIQUETES_ESTAT=config_web.ETIQUETES_ESTAT,
        COLORS_ESTAT=config_web.COLORS_ESTAT,
        COLORS_ESTAT_FONS=config_web.COLORS_ESTAT_FONS,
        COLORS_ESTAT_ACTIU_TEXT=config_web.COLORS_ESTAT_ACTIU_TEXT,
        COLORS_ESTAT_ACTIU_FONS=config_web.COLORS_ESTAT_ACTIU_FONS,
        ESTAT_PENDENT=config_web.ESTAT_PENDENT,
        ESTAT_COMPLETADA=config_web.ESTAT_COMPLETADA,
        ESTAT_PER_REVISAR=config_web.ESTAT_PER_REVISAR,
    )

    from routes.auth import auth_bp
    from routes.api import api_bp
    from routes.views import views_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
