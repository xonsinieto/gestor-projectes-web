"""
Client per a Microsoft Graph API.
Encapsula totes les operacions amb OneDrive.
"""
import json
import logging
from urllib.parse import quote

import requests

import config_web

logger = logging.getLogger(__name__)


class GraphClient:
    """Accedeix a fitxers d'OneDrive via Microsoft Graph API."""

    GRAPH_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str):
        self._token = access_token
        self._headers = {
            "Authorization": f"Bearer {access_token}",
        }

    def _get(self, url: str, **kwargs) -> requests.Response:
        resp = requests.get(url, headers=self._headers, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp

    def _put(self, url: str, data: bytes, content_type: str) -> requests.Response:
        headers = {**self._headers, "Content-Type": content_type}
        resp = requests.put(url, headers=headers, data=data, timeout=15)
        resp.raise_for_status()
        return resp

    # --- Operacions amb fitxers ---

    def llegir_fitxer_json(self, path: str) -> dict:
        """Llegeix un fitxer JSON d'OneDrive i retorna el contingut com a dict."""
        url = f"{self.GRAPH_URL}/me/drive/root:/{path}:/content"
        resp = self._get(url)
        return resp.json()

    def escriure_fitxer_json(self, path: str, dades: dict):
        """Escriu (o sobreescriu) un fitxer JSON a OneDrive."""
        url = f"{self.GRAPH_URL}/me/drive/root:/{path}:/content"
        contingut = json.dumps(dades, ensure_ascii=False, indent=2).encode("utf-8")
        self._put(url, contingut, "application/json")

    def obtenir_metadades(self, path: str) -> dict:
        """Obte les metadades d'un fitxer (eTag, lastModifiedDateTime, etc.)."""
        url = f"{self.GRAPH_URL}/me/drive/root:/{path}"
        resp = self._get(url, params={"select": "eTag,lastModifiedDateTime,size"})
        return resp.json()

    def obtenir_etag(self, path: str) -> str:
        """Retorna l'eTag del fitxer (per detectar canvis sense descarregar)."""
        try:
            meta = self.obtenir_metadades(path)
            return meta.get("eTag", "")
        except requests.HTTPError:
            return ""

    # --- Llistar carpetes i fitxers ---

    def llistar_carpetes(self, path: str) -> list[dict]:
        """Llista les subcarpetes d'una ruta a OneDrive.
        Retorna llista de {"name": "...", "folder": {...}}.
        """
        url = f"{self.GRAPH_URL}/me/drive/root:/{path}:/children"
        resp = self._get(url, params={
            "$filter": "folder ne null",
            "$select": "name,folder,lastModifiedDateTime",
            "$top": "200",
        })
        return resp.json().get("value", [])

    def llistar_fills(self, path: str) -> list[dict]:
        """Llista tots els fills (carpetes + fitxers) d'una ruta.
        Retorna llista de {"name": "...", "folder": {...} o absent, "size": ...}.
        """
        url = f"{self.GRAPH_URL}/me/drive/root:/{path}:/children"
        resp = self._get(url, params={
            "$select": "name,folder,file,size,lastModifiedDateTime,webUrl",
            "$top": "200",
        })
        return resp.json().get("value", [])

    # --- URLs de fitxers i carpetes ---

    def _encode_path(self, path: str) -> str:
        """Codifica cada segment del path per la Graph API (espais, accents, etc.)."""
        return "/".join(quote(segment, safe="") for segment in path.split("/"))

    def obtenir_url_item(self, path: str) -> str:
        """Obte la webUrl d'un fitxer o carpeta a OneDrive.
        Retorna la URL o cadena buida si falla.
        """
        # 1) Acces directe per path (requests auto-codifica)
        url1 = f"{self.GRAPH_URL}/me/drive/root:/{path}"
        logger.info(f"Graph API GET (directe): {url1}")
        try:
            resp = requests.get(url1, headers=self._headers, timeout=15)
            logger.info(f"Graph API response: {resp.status_code}")
            if resp.ok:
                data = resp.json()
                web_url = data.get("webUrl", "")
                if web_url:
                    logger.info(f"webUrl obtingut (directe): {web_url}")
                    return web_url
            else:
                logger.warning(f"Graph API error (directe): {resp.status_code} - {resp.text[:300]}")
        except requests.RequestException as e:
            logger.error(f"Graph API exception (directe): {e}")

        # 2) Acces amb codificacio manual per segment
        encoded = self._encode_path(path)
        url2 = f"{self.GRAPH_URL}/me/drive/root:/{encoded}"
        if url2 != url1:
            logger.info(f"Graph API GET (encoded): {url2}")
            try:
                resp2 = requests.get(url2, headers=self._headers, timeout=15)
                if resp2.ok:
                    data2 = resp2.json()
                    web_url2 = data2.get("webUrl", "")
                    if web_url2:
                        logger.info(f"webUrl obtingut (encoded): {web_url2}")
                        return web_url2
                else:
                    logger.warning(f"Graph API error (encoded): {resp2.status_code}")
            except requests.RequestException as e:
                logger.error(f"Graph API exception (encoded): {e}")

        # 3) Fallback: llistar carpeta pare i buscar el fitxer per nom
        parts = path.rsplit("/", 1)
        if len(parts) == 2:
            parent_path, filename = parts
            logger.info(f"Fallback: buscant '{filename}' dins '{parent_path}'")
            try:
                children_url = f"{self.GRAPH_URL}/me/drive/root:/{parent_path}:/children"
                resp3 = requests.get(
                    children_url, headers=self._headers, timeout=15,
                    params={"$select": "name,webUrl", "$top": "200"},
                )
                if resp3.ok:
                    for item in resp3.json().get("value", []):
                        if item.get("name", "").lower() == filename.lower():
                            web_url3 = item.get("webUrl", "")
                            logger.info(f"webUrl obtingut (per carpeta pare): {web_url3}")
                            return web_url3
                    logger.warning(f"Fitxer '{filename}' no trobat dins '{parent_path}'")
                else:
                    logger.warning(f"Error llistant carpeta pare: {resp3.status_code}")
            except requests.RequestException as e:
                logger.error(f"Exception buscant per carpeta pare: {e}")

        return ""

    def obtenir_link_compartit(self, path: str) -> str:
        """Obte la URL de visualitzacio d'un fitxer a OneDrive."""
        return self.obtenir_url_item(path)

    # --- Fotos d'usuari ---

    def obtenir_foto(self, nom_fitxer: str) -> bytes | None:
        """Descarrega una foto d'usuari de la carpeta de fotos a OneDrive."""
        path = f"{config_web.ONEDRIVE_PHOTOS_PATH}/{nom_fitxer}"
        url = f"{self.GRAPH_URL}/me/drive/root:/{path}:/content"
        try:
            resp = self._get(url)
            return resp.content
        except requests.HTTPError:
            return None
