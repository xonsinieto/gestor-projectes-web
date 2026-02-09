"""
Gestio de dades via Microsoft Graph API.
Equivalent web de services/data_manager.py del desktop.
"""
import uuid
from datetime import datetime

import config_web
from models.projecte import Projecte
from models.notificacio import Notificacio
from services.graph_client import GraphClient


class DataManagerWeb:
    """Llegeix i escriu dades_control.json via OneDrive Graph API."""

    def __init__(self, graph_client: GraphClient):
        self._graph = graph_client
        self._ultima_etag: str = ""
        self._projectes: dict[str, Projecte] = {}
        self._notificacions: list[Notificacio] = []
        self._usuaris: list[str] = []
        self._dades_raw: dict = {}

    @property
    def usuaris(self) -> list[str]:
        return self._usuaris

    def carregar(self) -> dict[str, Projecte]:
        """Carrega les dades del JSON d'OneDrive."""
        dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
        self._dades_raw = dades

        self._projectes = {}
        for nom_carpeta, dades_projecte in dades.get("projectes", {}).items():
            self._projectes[nom_carpeta] = Projecte.from_dict(
                nom_carpeta, dades_projecte
            )

        self._usuaris = dades.get("usuaris", [])

        self._notificacions = [
            Notificacio.from_dict(n) for n in dades.get("notificacions", [])
        ]

        self._ultima_etag = self._graph.obtenir_etag(config_web.ONEDRIVE_JSON_PATH)
        return self._projectes

    def desar(self, projectes: dict[str, Projecte]):
        """Desa els projectes al JSON d'OneDrive (preservant notificacions)."""
        dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
        dades["usuaris"] = self._usuaris
        dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
        dades["projectes"] = {nom: p.to_dict() for nom, p in projectes.items()}
        self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)
        self._projectes = projectes

    def ha_canviat(self) -> bool:
        """Comprova si el JSON ha estat modificat externament."""
        nova_etag = self._graph.obtenir_etag(config_web.ONEDRIVE_JSON_PATH)
        return nova_etag != self._ultima_etag

    # --- Notificacions ---

    def enviar_notificacio(
        self,
        de: str,
        per_a: str,
        projecte: str,
        tasca: str,
        accio: str,
        missatge: str = "",
    ):
        """Crea una notificacio al fitxer compartit."""
        notif = Notificacio(
            id=str(uuid.uuid4())[:8],
            de=de,
            per_a=per_a,
            projecte=projecte,
            tasca=tasca,
            accio=accio,
            missatge=missatge,
        )

        dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
        notificacions = dades.get("notificacions", [])
        notificacions.append(notif.to_dict())
        if len(notificacions) > 100:
            notificacions = notificacions[-100:]
        dades["notificacions"] = notificacions
        dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
        self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)

        self._notificacions.append(notif)

    def obtenir_notificacions(self, usuari: str) -> list[Notificacio]:
        """Retorna les notificacions pendents per a un usuari."""
        return [n for n in self._notificacions if n.per_a == usuari and not n.llegida]

    def marcar_llegida(self, notif_id: str):
        """Marca una notificacio com a llegida."""
        dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
        for n in dades.get("notificacions", []):
            if n.get("id") == notif_id:
                n["llegida"] = True
                break
        dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
        self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)

        for n in self._notificacions:
            if n.id == notif_id:
                n.llegida = True
                break

    def marcar_totes_llegides(self, usuari: str):
        """Marca totes les notificacions d'un usuari com a llegides."""
        dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
        for n in dades.get("notificacions", []):
            if n.get("per_a") == usuari:
                n["llegida"] = True
        dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
        self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)

        for n in self._notificacions:
            if n.per_a == usuari:
                n.llegida = True

    # --- Gestio d'usuaris ---

    def registrar_usuari(self, nom_usuari: str):
        """Registra un nou usuari al fitxer compartit."""
        dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
        usuaris = dades.get("usuaris", [])
        if nom_usuari not in usuaris:
            usuaris.append(nom_usuari)
            dades["usuaris"] = usuaris
            dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
            self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)
        self._usuaris = usuaris

    def eliminar_usuari(self, nom_usuari: str):
        """Elimina un usuari i desassigna les seves tasques."""
        dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
        usuaris = dades.get("usuaris", [])
        if nom_usuari in usuaris:
            usuaris.remove(nom_usuari)
            dades["usuaris"] = usuaris
            for proj_data in dades.get("projectes", {}).values():
                for tasca in proj_data.get("tasques", []):
                    if tasca.get("assignat") == nom_usuari:
                        tasca["assignat"] = ""
            dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
            self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)
        self._usuaris = usuaris

        for proj in self._projectes.values():
            for tasca in proj.tasques:
                if tasca.assignat == nom_usuari:
                    tasca.assignat = ""

    # --- Carpetes de projecte ---

    def llistar_carpetes_projecte(self) -> list[str]:
        """Llista les carpetes de projecte a OneDrive que coincideixen amb el patro."""
        try:
            carpetes = self._graph.llistar_carpetes(config_web.ONEDRIVE_BASE_PATH)
            noms = [c["name"] for c in carpetes if config_web.PATRO_PROJECTE.match(c["name"])]
            noms.sort(reverse=True)
            return noms
        except Exception:
            return []

    def llistar_fitxers_projecte(self, nom_projecte: str, subcarpeta: str = "") -> list[dict]:
        """Llista fitxers/carpetes dins un projecte (per al navegador de fitxers)."""
        path = f"{config_web.ONEDRIVE_BASE_PATH}/{nom_projecte}"
        if subcarpeta:
            path = f"{path}/{subcarpeta}"
        try:
            fills = self._graph.llistar_fills(path)
            resultat = []
            for item in fills:
                es_carpeta = "folder" in item
                resultat.append({
                    "nom": item["name"],
                    "es_carpeta": es_carpeta,
                    "mida": item.get("size", 0) if not es_carpeta else None,
                })
            resultat.sort(key=lambda x: (not x["es_carpeta"], x["nom"].lower()))
            return resultat
        except Exception:
            return []
