"""Réglages persistants (table settings) et fabrique des moteurs d'IA."""
from flask import current_app

import models
from services.claude_service import ClaudeCodeClient
from services.flashcard_generator import FlashcardGenerator
from services.ollama_service import OllamaClient

PROVIDERS = {
    "ollama": "Ollama, sur votre Mac",
    "claude": "Claude, avec votre abonnement",
}


def settings_defaults() -> dict:
    cfg = current_app.config
    return {
        "ai_provider": cfg["AI_PROVIDER"],
        "ollama_url": cfg["OLLAMA_URL"],
        "ollama_model": cfg["OLLAMA_MODEL"],
        "claude_model": cfg["CLAUDE_MODEL"],
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


def get_claude_client(model: str | None = None) -> ClaudeCodeClient:
    factory = current_app.config.get("CLAUDE_CLIENT_FACTORY", ClaudeCodeClient)
    s = current_settings()
    return factory(
        model=model or s["claude_model"],
        timeout=current_app.config["CLAUDE_TIMEOUT"],
        chunk_chars=current_app.config["CLAUDE_CHUNK_CHARS"],
    )


def get_generator(provider: str | None = None, model: str | None = None) -> FlashcardGenerator:
    """Moteur demandé, ou celui choisi par défaut dans les paramètres."""
    provider = provider or current_settings()["ai_provider"]
    if provider == "claude":
        return get_claude_client(model)
    return get_ollama_client(model)
