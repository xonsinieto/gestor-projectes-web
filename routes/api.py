"""
Blueprint API REST — Endpoints JSON per a crides AJAX des del frontend.
"""
from datetime import datetime

from flask import Blueprint, Response, jsonify, redirect, request, session

import config_web
from models.tasca import Tasca
from routes.auth import get_access_token
from services.graph_client import GraphClient
from services.data_manager_web import DataManagerWeb

api_bp = Blueprint("api", __name__)

# Cache de fotos a nivell de servidor (persistent entre requests)
_foto_cache: dict[str, tuple[bytes, str] | None] = {}


def _get_dm():
    """Obte un DataManagerWeb autenticat. Retorna (dm, error_response)."""
    token = get_access_token()
    if not token:
        return None, (jsonify({"error": "No autenticat"}), 401)
    graph = GraphClient(token)
    return DataManagerWeb(graph), None


def _get_usuari():
    """Retorna el nom de l'usuari actual de la sessio."""
    return session.get("usuari_actual", "")


# --- PROJECTES ---

@api_bp.route("/projectes")
def llistar_projectes():
    dm, err = _get_dm()
    if err:
        return err

    projectes = dm.carregar()
    persona = request.args.get("persona", "")
    cerca = request.args.get("cerca", "").lower()
    arxivats = request.args.get("arxivats", "") == "1"

    resultat = []
    for nom, proj in projectes.items():
        # Filtrar arxivats segons el parametre
        if not arxivats and proj.arxivat:
            continue
        if arxivats and not proj.arxivat:
            continue

        if cerca and cerca not in nom.lower():
            continue

        if persona:
            te_tasques = any(t.assignat == persona for t in proj.tasques)
            if not te_tasques:
                continue

        # Calcular quins usuaris tenen tasques i quins tenen pendents
        usuaris_implicats = set()
        usuaris_pendents = set()
        for t in proj.tasques:
            if t.assignat:
                usuaris_implicats.add(t.assignat)
                if t.estat != config_web.ESTAT_COMPLETADA:
                    usuaris_pendents.add(t.assignat)

        resultat.append({
            "nom_carpeta": nom,
            "codi": proj.codi,
            "descripcio": proj.descripcio,
            "total_tasques": proj.total_tasques,
            "tasques_completades": proj.tasques_completades,
            "percentatge": round(proj.percentatge, 1),
            "prioritari": proj.prioritari,
            "arxivat": proj.arxivat,
            "usuaris_implicats": list(usuaris_implicats),
            "usuaris_pendents": list(usuaris_pendents),
        })

    # Ordenar: prioritaris primer, despres per nom descendent (mes nous primer)
    resultat.sort(key=lambda p: p["nom_carpeta"], reverse=True)
    resultat.sort(key=lambda p: not p["prioritari"])

    return jsonify({
        "projectes": resultat,
        "usuaris": dm.usuaris,
        "resum": dm.obtenir_resum_usuaris(),
    })


@api_bp.route("/projectes/<path:nom>")
def detall_projecte(nom):
    dm, err = _get_dm()
    if err:
        return err

    projectes = dm.carregar()
    proj = projectes.get(nom)
    if not proj:
        return jsonify({"error": "Projecte no trobat"}), 404

    tasques = []
    for t in proj.tasques:
        tasques.append({
            "nom": t.nom,
            "estat": t.estat,
            "assignat": t.assignat,
            "observacions": t.observacions,
            "document": t.document,
            "data_modificacio": t.data_modificacio,
        })

    return jsonify({
        "nom_carpeta": nom,
        "codi": proj.codi,
        "descripcio": proj.descripcio,
        "total_tasques": proj.total_tasques,
        "tasques_completades": proj.tasques_completades,
        "percentatge": round(proj.percentatge, 1),
        "prioritari": proj.prioritari,
        "arxivat": proj.arxivat,
        "tasques": tasques,
        "usuaris": dm.usuaris,
        "resum": dm.obtenir_resum_usuaris(),
    })


@api_bp.route("/projectes", methods=["POST"])
def afegir_projecte():
    dm, err = _get_dm()
    if err:
        return err

    data = request.get_json()
    nom_carpeta = data.get("nom_carpeta", "").strip()
    if not nom_carpeta:
        return jsonify({"error": "Falta nom_carpeta"}), 400

    projectes = dm.carregar()
    if nom_carpeta in projectes:
        return jsonify({"error": "Projecte ja existeix"}), 409

    from models.projecte import Projecte
    projectes[nom_carpeta] = Projecte(nom_carpeta=nom_carpeta)
    dm.desar(projectes)
    return jsonify({"ok": True}), 201


@api_bp.route("/projectes/<path:nom>", methods=["DELETE"])
def eliminar_projecte(nom):
    dm, err = _get_dm()
    if err:
        return err

    projectes = dm.carregar()
    if nom not in projectes:
        return jsonify({"error": "Projecte no trobat"}), 404

    del projectes[nom]
    dm.desar(projectes)
    return jsonify({"ok": True})


@api_bp.route("/projectes/<path:nom>", methods=["PATCH"])
def actualitzar_projecte(nom):
    dm, err = _get_dm()
    if err:
        return err

    projectes = dm.carregar()
    proj = projectes.get(nom)
    if not proj:
        return jsonify({"error": "Projecte no trobat"}), 404

    data = request.get_json()
    if "arxivat" in data:
        proj.arxivat = bool(data["arxivat"])
    if "prioritari" in data:
        proj.prioritari = bool(data["prioritari"])

    dm.desar(projectes)
    return jsonify({"ok": True})


# --- TASQUES ---

@api_bp.route("/projectes/<path:nom>/tasques", methods=["POST"])
def afegir_tasques(nom):
    dm, err = _get_dm()
    if err:
        return err

    projectes = dm.carregar()
    proj = projectes.get(nom)
    if not proj:
        return jsonify({"error": "Projecte no trobat"}), 404

    data = request.get_json()
    noms_tasca = data.get("noms", [])
    assignat = data.get("assignat", "")

    noms_existents = {t.nom for t in proj.tasques}
    for nom_tasca in noms_tasca:
        if nom_tasca not in noms_existents:
            proj.tasques.append(Tasca(nom=nom_tasca, assignat=assignat))

    dm.desar(projectes)
    return jsonify({"ok": True}), 201


@api_bp.route("/projectes/<path:nom>/tasques/<path:nom_tasca>", methods=["DELETE"])
def eliminar_tasca(nom, nom_tasca):
    dm, err = _get_dm()
    if err:
        return err

    projectes = dm.carregar()
    proj = projectes.get(nom)
    if not proj:
        return jsonify({"error": "Projecte no trobat"}), 404

    proj.tasques = [t for t in proj.tasques if t.nom != nom_tasca]
    dm.desar(projectes)
    return jsonify({"ok": True})


@api_bp.route("/projectes/<path:nom>/tasques/<path:nom_tasca>", methods=["PATCH"])
def actualitzar_tasca(nom, nom_tasca):
    dm, err = _get_dm()
    if err:
        return err

    projectes = dm.carregar()
    proj = projectes.get(nom)
    if not proj:
        return jsonify({"error": "Projecte no trobat"}), 404

    tasca = next((t for t in proj.tasques if t.nom == nom_tasca), None)
    if not tasca:
        return jsonify({"error": "Tasca no trobada"}), 404

    data = request.get_json()
    usuari = _get_usuari()

    if "estat" in data:
        nou_estat = data["estat"]
        tasca.actualitzar_estat(nou_estat)

        # Notificacions s'acumulen en memoria (es desen amb desar())
        if nou_estat == config_web.ESTAT_ENVIAT and tasca.assignat:
            dm.enviar_notificacio(
                de=usuari, per_a=tasca.assignat, projecte=nom,
                tasca=nom_tasca, accio="enviat",
            )
        elif nou_estat == config_web.ESTAT_PER_REVISAR:
            revisor = data.get("revisor", "")
            if revisor:
                tasca.assignar_a(revisor)
                dm.enviar_notificacio(
                    de=usuari, per_a=revisor, projecte=nom,
                    tasca=nom_tasca, accio="per_revisar",
                )
        elif nou_estat == config_web.ESTAT_COMPLETADA:
            for u in dm.usuaris:
                if u != usuari:
                    dm.enviar_notificacio(
                        de=usuari, per_a=u, projecte=nom,
                        tasca=nom_tasca, accio="completada",
                    )

    if "assignat" in data:
        tasca.assignar_a(data["assignat"])

    if "observacions" in data:
        tasca.observacions = data["observacions"]
        tasca.data_modificacio = datetime.now().isoformat(timespec="seconds")

    if "document" in data:
        tasca.document = data["document"]
        tasca.data_modificacio = datetime.now().isoformat(timespec="seconds")

    # UNA sola escriptura (projectes + notificacions acumulades)
    dm.desar(projectes)
    return jsonify({"ok": True})


# --- NOTIFICACIONS ---

@api_bp.route("/notificacions")
def obtenir_notificacions():
    dm, err = _get_dm()
    if err:
        return err

    usuari = _get_usuari()
    dm.carregar()
    notifs = dm.obtenir_notificacions(usuari)
    return jsonify([n.to_dict() for n in notifs])


@api_bp.route("/notificacions/<notif_id>/llegida", methods=["POST"])
def marcar_notif_llegida(notif_id):
    dm, err = _get_dm()
    if err:
        return err

    dm.carregar()
    dm.marcar_llegida(notif_id)
    return jsonify({"ok": True})


@api_bp.route("/notificacions/totes-llegides", methods=["POST"])
def marcar_totes_notifs_llegides():
    dm, err = _get_dm()
    if err:
        return err

    dm.carregar()
    dm.marcar_totes_llegides(_get_usuari())
    return jsonify({"ok": True})


# --- USUARIS ---

@api_bp.route("/usuaris")
def llistar_usuaris():
    dm, err = _get_dm()
    if err:
        return err

    dm.carregar()
    return jsonify(dm.usuaris)


@api_bp.route("/usuaris", methods=["POST"])
def afegir_usuari():
    dm, err = _get_dm()
    if err:
        return err

    data = request.get_json()
    nom = data.get("nom", "").strip()
    if not nom:
        return jsonify({"error": "Falta nom"}), 400

    dm.carregar()
    dm.registrar_usuari(nom)
    return jsonify({"ok": True}), 201


@api_bp.route("/usuaris/<path:nom>", methods=["DELETE"])
def eliminar_usuari(nom):
    dm, err = _get_dm()
    if err:
        return err

    dm.carregar()
    dm.eliminar_usuari(nom)
    return jsonify({"ok": True})


# --- FOTOS D'USUARI ---

@api_bp.route("/foto/<path:nom>")
def obtenir_foto_usuari(nom):
    """Serveix la foto d'un usuari des d'OneDrive.
    Naming: primer mot en minuscula (ex: 'Alfons Vigas' -> 'alfons.png').
    """
    nom_base = nom.split()[0].lower() if nom.strip() else nom.lower()

    # Cache servidor (fotos no canvien gaire)
    if nom_base in _foto_cache:
        cached = _foto_cache[nom_base]
        if cached is None:
            return "", 404
        return Response(cached[0], mimetype=cached[1],
                        headers={"Cache-Control": "public, max-age=3600"})

    token = get_access_token()
    if not token:
        _foto_cache[nom_base] = None
        return "", 404

    graph = GraphClient(token)
    for ext in ["png", "jpg", "jpeg"]:
        foto = graph.obtenir_foto(f"{nom_base}.{ext}")
        if foto:
            content_type = "image/png" if ext == "png" else "image/jpeg"
            _foto_cache[nom_base] = (foto, content_type)
            return Response(foto, mimetype=content_type,
                            headers={"Cache-Control": "public, max-age=3600"})

    _foto_cache[nom_base] = None
    return "", 404


# --- OBRIR DOCUMENTS ---

@api_bp.route("/obrir-document/<path:ruta>")
def obrir_document(ruta):
    """Obte la URL de visualitzacio d'un fitxer d'OneDrive."""
    import logging
    logger = logging.getLogger(__name__)

    token = get_access_token()
    if not token:
        return jsonify({"error": "No autenticat"}), 401

    # Normalitzar backslashes (paths del desktop poden tenir \\)
    ruta = ruta.replace("\\", "/")

    graph = GraphClient(token)
    full_path = f"{config_web.ONEDRIVE_BASE_PATH}/{ruta}"
    logger.info(f"Obrint document: ruta={ruta}, full_path={full_path}")

    # Intentar obtenir URL del fitxer (amb 3 fallbacks interns)
    link = graph.obtenir_url_item(full_path)
    if link:
        logger.info(f"Document obert OK: {link[:100]}")
        return jsonify({"url": link})

    # Ultim recurs: obrir la carpeta pare
    logger.warning(f"No s'ha pogut obtenir URL del document: {full_path}")
    parts = ruta.rsplit("/", 1)
    if len(parts) > 1:
        folder_path = f"{config_web.ONEDRIVE_BASE_PATH}/{parts[0]}"
        logger.info(f"Ultim recurs: carpeta pare: {folder_path}")
        folder_link = graph.obtenir_url_item(folder_path)
        if folder_link:
            return jsonify({"url": folder_link, "es_carpeta": True})

    return jsonify({"error": f"No s'ha trobat: {ruta}"}), 404


@api_bp.route("/redir-document/<path:ruta>")
def redir_document(ruta):
    """Redirigeix directament a la URL del document a OneDrive (per a <a> links)."""
    import logging
    logger = logging.getLogger(__name__)

    token = get_access_token()
    if not token:
        return "No autenticat. <a href='/auth/login'>Inicia sessio</a>", 401

    ruta = ruta.replace("\\", "/")
    graph = GraphClient(token)
    full_path = f"{config_web.ONEDRIVE_BASE_PATH}/{ruta}"
    logger.info(f"Redirect document: {full_path}")

    link = graph.obtenir_url_item(full_path)
    if link:
        logger.info(f"Redirect OK: {link[:100]}")
        return redirect(link)

    # Fallback: carpeta pare
    parts = ruta.rsplit("/", 1)
    if len(parts) > 1:
        folder_path = f"{config_web.ONEDRIVE_BASE_PATH}/{parts[0]}"
        folder_link = graph.obtenir_url_item(folder_path)
        if folder_link:
            logger.info(f"Redirect fallback carpeta: {folder_link[:100]}")
            return redirect(folder_link)

    return f"No s'ha trobat el document: {ruta}", 404


@api_bp.route("/obrir-carpeta/<path:nom_projecte>")
def obrir_carpeta(nom_projecte):
    """Obte la URL de la carpeta d'un projecte a OneDrive."""
    token = get_access_token()
    if not token:
        return jsonify({"error": "No autenticat"}), 401

    graph = GraphClient(token)
    folder_path = f"{config_web.ONEDRIVE_BASE_PATH}/{nom_projecte}"
    link = graph.obtenir_url_item(folder_path)
    if link:
        return jsonify({"url": link})
    return jsonify({"error": "Carpeta no trobada"}), 404


# --- ONEDRIVE: CARPETES I FITXERS ---

@api_bp.route("/carpetes-onedrive")
def llistar_carpetes_onedrive():
    dm, err = _get_dm()
    if err:
        return err

    dm.carregar()
    existents = set(dm._projectes.keys())
    carpetes = dm.llistar_carpetes_projecte()
    return jsonify([
        {"nom": c, "ja_afegit": c in existents}
        for c in carpetes
    ])


@api_bp.route("/fitxers/<path:nom_projecte>")
def llistar_fitxers(nom_projecte):
    dm, err = _get_dm()
    if err:
        return err

    subcarpeta = request.args.get("subcarpeta", "")
    fitxers = dm.llistar_fitxers_projecte(nom_projecte, subcarpeta)
    return jsonify(fitxers)


# --- PLANTILLES ---

@api_bp.route("/plantilles")
def obtenir_plantilles():
    return jsonify(config_web.DOCUMENTS)


# --- SYNC ---

@api_bp.route("/ha-canviat")
def ha_canviat():
    dm, err = _get_dm()
    if err:
        return err

    etag_anterior = session.get("ultima_etag", "")
    nova_etag = dm._graph.obtenir_etag(config_web.ONEDRIVE_JSON_PATH)
    canviat = nova_etag != etag_anterior
    if canviat:
        session["ultima_etag"] = nova_etag
        DataManagerWeb.invalidar_cache()
    return jsonify({"canviat": canviat})
