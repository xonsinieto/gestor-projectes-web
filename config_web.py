"""
Configuracio web del Gestor de Projectes.
Constants compartides amb l'app desktop + config Azure OAuth.
"""
import os
import re

from dotenv import load_dotenv
load_dotenv()

# --- Azure OAuth ---
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_TENANT = "common"
AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT}"
AZURE_SCOPES = ["Files.ReadWrite", "User.Read"]
AZURE_REDIRECT_PATH = "/auth/callback"

# --- Llista blanca d'emails autoritzats ---
# Nomes aquests comptes de Microsoft poden accedir a l'app.
# Configurable via variable d'entorn (emails separats per comes) o aqui directament.
_emails_env = os.environ.get("EMAILS_AUTORITZATS", "")
EMAILS_AUTORITZATS = [
    e.strip().lower() for e in _emails_env.split(",") if e.strip()
] if _emails_env else [
    # Afegeix aqui els emails dels teus usuaris:
    # "alfons@outlook.com",
    # "dani@gmail.com",
]

# --- Ruta del JSON a OneDrive ---
ONEDRIVE_BASE_PATH = os.environ.get(
    "ONEDRIVE_BASE_PATH", "ARQUITECTURA ALFONS VIGAS"
)
ONEDRIVE_DATA_FOLDER = os.environ.get(
    "ONEDRIVE_DATA_FOLDER", "GESTOR DE PROJECTES"
)
ONEDRIVE_JSON_PATH = f"{ONEDRIVE_BASE_PATH}/{ONEDRIVE_DATA_FOLDER}/dades_control.json"
ONEDRIVE_PHOTOS_PATH = f"{ONEDRIVE_BASE_PATH}/{ONEDRIVE_DATA_FOLDER}/fotos"

# --- Flask ---
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-canvia-en-produccio")

# --- Estats de tasca (identics al desktop config.py) ---
ESTAT_PENDENT = "pendent"
ESTAT_ENVIAT = "enviat"
ESTAT_EN_CURS = "en_curs"
ESTAT_PER_REVISAR = "per_revisar"
ESTAT_COMPLETADA = "completada"

ESTATS = [ESTAT_PENDENT, ESTAT_ENVIAT, ESTAT_EN_CURS, ESTAT_PER_REVISAR, ESTAT_COMPLETADA]

ETIQUETES_ESTAT = {
    ESTAT_PENDENT: "Pendent",
    ESTAT_ENVIAT: "Enviat",
    ESTAT_EN_CURS: "En curs",
    ESTAT_PER_REVISAR: "Per revisar",
    ESTAT_COMPLETADA: "Completada",
}

COLORS_ESTAT = {
    ESTAT_PENDENT: "#9CA3AF",
    ESTAT_ENVIAT: "#F59E0B",
    ESTAT_EN_CURS: "#3B82F6",
    ESTAT_PER_REVISAR: "#EF4444",
    ESTAT_COMPLETADA: "#10B981",
}

COLORS_ESTAT_FONS = {
    ESTAT_PENDENT: "#F3F4F6",
    ESTAT_ENVIAT: "#FEF3C7",
    ESTAT_EN_CURS: "#DBEAFE",
    ESTAT_PER_REVISAR: "#FEE2E2",
    ESTAT_COMPLETADA: "#D1FAE5",
}

COLORS_ESTAT_ACTIU_TEXT = {
    ESTAT_PENDENT: "#374151",
    ESTAT_ENVIAT: "#92400E",
    ESTAT_EN_CURS: "#1E40AF",
    ESTAT_PER_REVISAR: "#991B1B",
    ESTAT_COMPLETADA: "#065F46",
}

COLORS_ESTAT_ACTIU_FONS = {
    ESTAT_PENDENT: "#D1D5DB",
    ESTAT_ENVIAT: "#FDE68A",
    ESTAT_EN_CURS: "#BFDBFE",
    ESTAT_PER_REVISAR: "#FECACA",
    ESTAT_COMPLETADA: "#A7F3D0",
}

# --- Patro de noms de carpeta de projectes ---
PATRO_PROJECTE = re.compile(r"^(20\d{2,6})_(.+)$")

# --- Plantilles de tasques (identic a services/plantilles_tasques.py) ---
DOCUMENTS = {
    "Planols de": [
        "Projecte Basic",
        "Projecte Executiu",
        "Projecte Basic i Executiu",
        "Planols Altres",
    ],
    "Memoria Projectes": [
        "Projecte Basic",
        "Projecte Basic i Executiu",
        "Fitxes Basic",
        "Fitxes Executiu",
        "Fitxes Basic i Executiu",
        "Estudi Gestio Residus",
        "Quadre Normativa",
        "Quadre de Superficies Habitatge",
        "Justificacio Edificabilitat",
        "Justificacio Ocupacio",
        "Muntatge Final de Projecte Basic",
        "Muntatge Final de Projecte Executiu",
        "Muntatge Final de Projecte Basic i Executiu",
    ],
    "Amidaments": [
        "Amidaments de Projecte",
        "Amidaments Altres",
    ],
    "Seguretat i Salut": [
        "EBSS (Estudi Basic Seguretat i Salut)",
        "Coordinador Seguretat i Salut",
    ],
    "Assumeix de Direccio": [
        "ASSUMEIX (Assumpcio Direccio d'Obra)",
    ],
    "Residus i Medi Ambient": [
        "Estudi Gestio de Residus",
        "Llicencia Ambiental (si s'escau)",
    ],
    "Certificat Energetic": [
        "Certificat Energetic (CE3X o HULC)",
    ],
    "Cedula d'Habitabilitat": [
        "Cedula Habitabilitat (si s'escau)",
    ],
    "Certificats Arquitecte": [
        "Certificat Solidesa",
        "Certificat Antiguitat",
        "Certificat Altres",
    ],
    "Representacions": [
        "Autoritzacio Telematica",
    ],
    "Finals d'Obres": [
        "Annex A (Certificat Final d'Obres)",
        "900D Model de Representacio (Cadastre)",
        "Instancia Primera Ocupacio",
        "Entrega Final Ajuntament",
    ],
}
