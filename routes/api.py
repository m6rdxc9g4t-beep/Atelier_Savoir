"""API REST JSON d'Atelier_Savoir (préfixe /api)."""
import os
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

import models
from services.settings_service import current_settings, get_ollama_client
from services.ollama_service import OllamaError
from services.spaced_repetition import RATINGS
from services.text_extraction import ExtractionError, extract_text, source_type_for

api = Blueprint("api", __name__, url_prefix="/api")


def error(message, status=400):
    return jsonify({"error": message}), status


def body():
    return request.get_json(silent=True) or {}


def _int_arg(name, default=None):
    value = request.args.get(name)
    try:
        return int(value) if value not in (None, "") else default
    except ValueError:
        return default


def _remove_upload(stored_path):
    if not stored_path:
        return
    path = Path(current_app.config["UPLOAD_FOLDER"]) / stored_path
    try:
        path.unlink(missing_ok=True)
    except OSError:
        current_app.logger.warning("Fichier non supprimé : %s", path)


@api.errorhandler(413)
def too_large(_e):
    limit = current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return error(f"Fichier trop volumineux (limite : {limit} Mo).", 413)


# --------------------------------------------------------------------- cours
@api.get("/courses")
def courses_index():
    return jsonify(models.list_courses())


@api.post("/courses")
def courses_create():
    data = body()
    title = (data.get("title") or "").strip()
    if not title:
        return error("Donnez un titre au cours.")
    course = models.create_course(title, data.get("subject", ""), data.get("description", ""))
    return jsonify(course), 201


@api.get("/courses/<int:course_id>")
def courses_show(course_id):
    course = models.get_course(course_id)
    if course is None:
        return error("Cours introuvable.", 404)
    course["chapters"] = models.list_chapters(course_id)
    return jsonify(course)


@api.patch("/courses/<int:course_id>")
def courses_update(course_id):
    if models.get_course(course_id) is None:
        return error("Cours introuvable.", 404)
    data = body()
    if "title" in data and not str(data["title"]).strip():
        return error("Le titre ne peut pas être vide.")
    return jsonify(models.update_course(course_id, **data))


@api.delete("/courses/<int:course_id>")
def courses_delete(course_id):
    deleted, paths = models.delete_course(course_id)
    if not deleted:
        return error("Cours introuvable.", 404)
    for path in paths:
        _remove_upload(path)
    return jsonify({"deleted": True})


# ----------------------------------------------------------------- chapitres
@api.post("/courses/<int:course_id>/chapters")
def chapters_create(course_id):
    """Ajoute un chapitre : fichier (multipart « file ») ou texte collé (« content »)."""
    if models.get_course(course_id) is None:
        return error("Cours introuvable.", 404)

    upload = request.files.get("file")
    form = request.form if request.form or upload else body()
    title = (form.get("title") or "").strip()

    if upload and upload.filename:
        filename = upload.filename
        if source_type_for(filename) is None:
            return error("Format non pris en charge. Importez un fichier .md, .txt ou .pdf.")
        data = upload.read()
        try:
            content = extract_text(filename, data)
        except ExtractionError as exc:
            return error(str(exc), 422)
        safe = secure_filename(filename) or "cours"
        stored = f"{course_id}/{uuid.uuid4().hex[:8]}_{safe}"
        dest = Path(current_app.config["UPLOAD_FOLDER"]) / stored
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        chapter = models.create_chapter(
            course_id, title or os.path.splitext(filename)[0], content,
            source_type=source_type_for(filename), source_filename=filename, stored_path=stored)
        return jsonify(chapter), 201

    content = (form.get("content") or "").strip()
    if not content:
        return error("Ajoutez un fichier ou collez le texte du chapitre.")
    if not title:
        return error("Donnez un titre au chapitre.")
    chapter = models.create_chapter(course_id, title, content, source_type="texte")
    return jsonify(chapter), 201


@api.get("/chapters/<int:chapter_id>")
def chapters_show(chapter_id):
    chapter = models.get_chapter(chapter_id)
    if chapter is None:
        return error("Chapitre introuvable.", 404)
    chapter.pop("stored_path", None)
    return jsonify(chapter)


@api.delete("/chapters/<int:chapter_id>")
def chapters_delete(chapter_id):
    deleted, stored = models.delete_chapter(chapter_id)
    if not deleted:
        return error("Chapitre introuvable.", 404)
    _remove_upload(stored)
    return jsonify({"deleted": True})


@api.post("/chapters/<int:chapter_id>/generate")
def chapters_generate(chapter_id):
    """Propose des flashcards générées par Ollama (rien n'est enregistré ici)."""
    chapter = models.get_chapter(chapter_id)
    if chapter is None:
        return error("Chapitre introuvable.", 404)
    data = body()
    try:
        max_cards = int(data.get("max_cards") or current_settings()["cards_per_chapter"])
    except (TypeError, ValueError):
        return error("Le nombre de cartes doit être un entier.")
    max_cards = max(1, min(max_cards, 60))

    client = get_ollama_client(data.get("model") or None)
    course = models.get_course(chapter["course_id"])
    try:
        cards = client.generate_flashcards(
            chapter["content"],
            title=f"{course['title']} — {chapter['title']}",
            max_cards=max_cards,
            exclude_questions=models.existing_questions(chapter_id),
        )
    except OllamaError as exc:
        return error(str(exc), 502)
    return jsonify({"chapter_id": chapter_id, "course_id": chapter["course_id"],
                    "model": client.model, "cards": cards})


# ---------------------------------------------------------------- flashcards
@api.get("/flashcards")
def flashcards_index():
    return jsonify(models.list_flashcards(_int_arg("course_id"), _int_arg("chapter_id")))


@api.post("/flashcards")
def flashcards_create():
    """Enregistre une ou plusieurs cartes : {course_id, chapter_id?, origin?, cards: [...]}."""
    data = body()
    course_id = data.get("course_id")
    chapter_id = data.get("chapter_id")
    if chapter_id is not None:
        chapter = models.get_chapter(chapter_id, with_content=False)
        if chapter is None:
            return error("Chapitre introuvable.", 404)
        course_id = chapter["course_id"]
    if course_id is None or models.get_course(course_id) is None:
        return error("Cours introuvable.", 404)

    raw_cards = data.get("cards")
    if raw_cards is None and data.get("question"):
        raw_cards = [data]
    cards = [c for c in (raw_cards or [])
             if isinstance(c, dict)
             and str(c.get("question", "")).strip() and str(c.get("answer", "")).strip()]
    if not cards:
        return error("Aucune carte valide : chaque carte doit avoir une question et une réponse.")
    origin = "ia" if data.get("origin") == "ia" else "manuel"
    created = models.create_flashcards(course_id, chapter_id, cards, origin)
    return jsonify({"created": len(created), "cards": created}), 201


@api.patch("/flashcards/<int:card_id>")
def flashcards_update(card_id):
    if models.get_flashcard(card_id) is None:
        return error("Carte introuvable.", 404)
    data = body()
    if "type" in data and "card_type" not in data:
        data["card_type"] = data["type"]
    return jsonify(models.update_flashcard(card_id, **data))


@api.delete("/flashcards/<int:card_id>")
def flashcards_delete(card_id):
    if not models.delete_flashcard(card_id):
        return error("Carte introuvable.", 404)
    return jsonify({"deleted": True})


@api.post("/flashcards/<int:card_id>/review")
def flashcards_review(card_id):
    rating = body().get("rating")
    if rating not in RATINGS:
        return error("Note invalide : utilisez a_revoir, correct ou maitrise.")
    card = models.review_flashcard(card_id, rating)
    if card is None:
        return error("Carte introuvable.", 404)
    return jsonify(card)


# ------------------------------------------------------------------ révision
@api.get("/study/session")
def study_session():
    mode = request.args.get("mode", "dues")
    limit = max(1, min(_int_arg("limit", 30), 200))
    cards = models.study_queue(_int_arg("course_id"), mode=mode, limit=limit)
    return jsonify({"mode": mode, "cards": cards})


@api.get("/stats")
def stats():
    return jsonify(models.global_stats())


# ----------------------------------------------------------- Ollama & réglages
@api.get("/ollama/status")
def ollama_status():
    return jsonify(get_ollama_client().status())


@api.get("/settings")
def settings_show():
    return jsonify(current_settings())


@api.put("/settings")
def settings_update():
    data = body()
    values = {}
    if "ollama_url" in data:
        url = str(data["ollama_url"]).strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            return error("L'adresse d'Ollama doit commencer par http:// ou https://.")
        values["ollama_url"] = url
    if "ollama_model" in data:
        model = str(data["ollama_model"]).strip()
        if not model:
            return error("Choisissez un modèle.")
        values["ollama_model"] = model
    if "cards_per_chapter" in data:
        try:
            n = int(data["cards_per_chapter"])
        except (TypeError, ValueError):
            return error("Le nombre de cartes doit être un entier.")
        values["cards_per_chapter"] = max(1, min(n, 60))
    models.save_settings(values)
    return jsonify(current_settings())
