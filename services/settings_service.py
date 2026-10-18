"""Réglages persistants (table settings) et fabrique du client Ollama."""
from flask import current_app

import models
from services.ollama_service import OllamaClient


def settings_defaults() -> dict:
    cfg = current_app.config
    return {
        "ollama_url": cfg["OLLAMA_URL"],
        "ollama_model": cfg["OLLAMA_MODEL"],
        "cards_per_chapter": str(cfg["CARDS_PER_CHAPTER"]),
    }


def current_settings() -> dict:
    return models.get_settings(settings_defaults())


def get_ollama_client(model: str | None = None) -> OllamaClient:
    """Client Ollama configuré avec les réglages enregistrés (ou ceux par défaut)."""
    factory = current_app.config.get("OLLAMA_CLIENT_FACTORY", OllamaClient)
    s = current_settings()
    return factory(
        base_url=s["ollama_url"],
        model=model or s["ollama_model"],
        timeout=current_app.config["OLLAMA_TIMEOUT"],
        chunk_chars=current_app.config["CHUNK_CHARS"],
    )
