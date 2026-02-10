"""
Gestio de dades via Microsoft Graph API.
Equivalent web de services/data_manager.py del desktop.
"""
import time
import uuid
from datetime import datetime

import config_web
from models.projecte import Projecte
from models.notificacio import Notificacio
from services.graph_client import GraphClient


class DataManagerWeb:
    """Llegeix i escriu dades_control.json via OneDrive Graph API."""

    # Cache compartit a nivell de classe (persistent entre requests)
    _cache_dades: dict | None = None
    _cache_time: float = 0
    CACHE_TTL = 30  # segons

    def __init__(self, graph_client: GraphClient):
        self._graph = graph_client
        self._projectes: dict[str, Projecte] = {}
        self._notificacions: list[Notificacio] = []
        self._usuaris: list[str] = []
        self._dades_raw: dict = {}
        self._notificacions_noves: list[dict] = []  # Acumula per desar d'un cop

    @property
    def usuaris(self) -> list[str]:
        return self._usuaris

    def carregar(self, force: bool = False) -> dict[str, Projecte]:
        """Carrega les dades del JSON d'OneDrive (amb cache TTL)."""
        now = time.time()

        if (not force
                and DataManagerWeb._cache_dades is not None
                and (now - DataManagerWeb._cache_time) < DataManagerWeb.CACHE_TTL):
            dades = DataManagerWeb._cache_dades
        else:
            dades = self._graph.llegir_fitxer_json(config_web.ONEDRIVE_JSON_PATH)
            DataManagerWeb._cache_dades = dades
            DataManagerWeb._cache_time = now

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

        return self._projectes

    def desar(self, projectes: dict[str, Projecte]):
        """Desa projectes + notificacions acumulades en UNA sola escriptura."""
        dades = dict(self._dades_raw)
        dades["usuaris"] = self._usuaris
        dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
        dades["projectes"] = {nom: p.to_dict() for nom, p in projectes.items()}

        # Incloure notificacions noves acumulades (0 lectures extra!)
        if self._notificacions_noves:
            notificacions = list(dades.get("notificacions", []))
            notificacions.extend(self._notificacions_noves)
            if len(notificacions) > 100:
                notificacions = notificacions[-100:]
            dades["notificacions"] = notificacions
            self._notificacions_noves = []

        self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)
        self._projectes = projectes

        # Actualitzar cache
        DataManagerWeb._cache_dades = dades
        DataManagerWeb._cache_time = time.time()

    @staticmethod
    def invalidar_cache():
        """Invalida el cache per forcar una lectura fresca."""
        DataManagerWeb._cache_dades = None

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
        """Acumula una notificacio (es desara amb desar() — 0 lectures extra)."""
        notif = Notificacio(
            id=str(uuid.uuid4())[:8],
            de=de,
            per_a=per_a,
            projecte=projecte,
            tasca=tasca,
            accio=accio,
            missatge=missatge,
        )
        self._notificacions_noves.append(notif.to_dict())
        self._notificacions.append(notif)

    def obtenir_notificacions(self, usuari: str) -> list[Notificacio]:
        """Retorna les notificacions pendents per a un usuari."""
        return [n for n in self._notificacions if n.per_a == usuari and not n.llegida]

    def marcar_llegida(self, notif_id: str):
        """Marca una notificacio com a llegida (usa dades cached)."""
        dades = dict(self._dades_raw)
        for n in dades.get("notificacions", []):
            if n.get("id") == notif_id:
                n["llegida"] = True
                break
        dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
        self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)

        DataManagerWeb._cache_dades = dades
        DataManagerWeb._cache_time = time.time()

        for n in self._notificacions:
            if n.id == notif_id:
                n.llegida = True
                break

    def marcar_totes_llegides(self, usuari: str):
        """Marca totes les notificacions d'un usuari com a llegides (usa dades cached)."""
        dades = dict(self._dades_raw)
        for n in dades.get("notificacions", []):
            if n.get("per_a") == usuari:
                n["llegida"] = True
        dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
        self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)

        DataManagerWeb._cache_dades = dades
        DataManagerWeb._cache_time = time.time()

        for n in self._notificacions:
            if n.per_a == usuari:
                n.llegida = True

    # --- Gestio d'usuaris ---

    def registrar_usuari(self, nom_usuari: str):
        """Registra un nou usuari al fitxer compartit."""
        if nom_usuari not in self._usuaris:
            self._usuaris.append(nom_usuari)
            dades = dict(self._dades_raw)
            dades["usuaris"] = self._usuaris
            dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
            self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)
            DataManagerWeb._cache_dades = dades
            DataManagerWeb._cache_time = time.time()

    def eliminar_usuari(self, nom_usuari: str):
        """Elimina un usuari i desassigna les seves tasques."""
        if nom_usuari in self._usuaris:
            self._usuaris.remove(nom_usuari)
            dades = dict(self._dades_raw)
            dades["usuaris"] = self._usuaris
            for proj_data in dades.get("projectes", {}).values():
                for tasca in proj_data.get("tasques", []):
                    if tasca.get("assignat") == nom_usuari:
                        tasca["assignat"] = ""
            dades["ultima_modificacio"] = datetime.now().isoformat(timespec="seconds")
            self._graph.escriure_fitxer_json(config_web.ONEDRIVE_JSON_PATH, dades)
            DataManagerWeb._cache_dades = dades
            DataManagerWeb._cache_time = time.time()

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
                    "webUrl": item.get("webUrl", ""),
                })
            resultat.sort(key=lambda x: (not x["es_carpeta"], x["nom"].lower()))
            return resultat
        except Exception:
            return []

    # --- Resum per a barra inferior ---

    def obtenir_resum_usuaris(self) -> list[dict]:
        """Retorna el resum de tasques per usuari (identic al desktop)."""
        resum = []
        for usuari in self._usuaris:
            nom_curt = usuari.split()[0]
            enviades = 0
            en_curs = 0
            per_revisar = 0
            fetes = 0
            for proj in self._projectes.values():
                for tasca in proj.tasques:
                    if tasca.assignat == usuari:
                        if tasca.estat == config_web.ESTAT_ENVIAT:
                            enviades += 1
                        elif tasca.estat == config_web.ESTAT_EN_CURS:
                            en_curs += 1
                        elif tasca.estat == config_web.ESTAT_PER_REVISAR:
                            per_revisar += 1
                        elif tasca.estat == config_web.ESTAT_COMPLETADA:
                            fetes += 1
            resum.append({
                "nom": nom_curt,
                "enviades": enviades,
                "en_curs": en_curs,
                "per_revisar": per_revisar,
                "fetes": fetes,
            })
        return resum
