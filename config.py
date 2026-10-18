"""Configuration d'Atelier_Savoir.

Toutes les valeurs peuvent être surchargées par des variables d'environnement.
Les réglages Ollama modifiables depuis l'interface (/settings) sont stockés
dans la table `settings` et priment sur ces valeurs par défaut.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "atelier-savoir-dev")

    # Base SQLite locale (spécification : savoir.db)
    DATABASE = os.environ.get("ATELIER_DB", str(BASE_DIR / "instance" / "savoir.db"))

    # Fichiers de cours importés (conservés tels quels)
    UPLOAD_FOLDER = os.environ.get("ATELIER_UPLOADS", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 Mo par import
    ALLOWED_EXTENSIONS = {"md", "markdown", "txt", "pdf"}

    # IA locale
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
    OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))  # secondes
    CARDS_PER_CHAPTER = int(os.environ.get("ATELIER_CARDS_PER_CHAPTER", "15"))
    CHUNK_CHARS = int(os.environ.get("ATELIER_CHUNK_CHARS", "6000"))


class TestConfig(Config):
    TESTING = True
