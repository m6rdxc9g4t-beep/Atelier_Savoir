"""Moteur local : API Ollama (http://localhost:11434).

Ollama est interrogé via /api/chat avec une sortie structurée (paramètre
`format` = schéma JSON). Prompt, découpage et analyse : services/flashcard_generator.py.
"""
import requests

from services.flashcard_generator import (  # noqa: F401  (réexportés)
    CARD_TYPES, FLASHCARD_SCHEMA, FlashcardGenerator, GenerationError, parse_flashcards,
)


class OllamaError(GenerationError):
    """Erreur lisible par l'utilisateur lors d'un appel à Ollama."""


class OllamaClient(FlashcardGenerator):
    provider = "ollama"
    label = "Ollama"

    def __init__(self, base_url="http://localhost:11434", model="llama3.1", timeout=300,
                 chunk_chars=6000, session=None):
        super().__init__(model, chunk_chars)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.http = session or requests.Session()

    # ----------------------------------------------------------- bas niveau
    def _request(self, method, path, timeout=None, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            response = self.http.request(method, url, timeout=timeout or self.timeout, **kwargs)
        except requests.ConnectionError as exc:
            raise OllamaError(
                f"Impossible de joindre Ollama sur {self.base_url}. "
                "Vérifiez qu'il est lancé (commande : ollama serve).") from exc
        except requests.Timeout as exc:
            raise OllamaError(
                "Ollama n'a pas répondu à temps. Essayez un modèle plus léger "
                "ou augmentez OLLAMA_TIMEOUT.") from exc
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", response.text)
            except ValueError:
                detail = response.text
            if response.status_code == 404 and "not found" in str(detail):
                raise OllamaError(
                    f"Le modèle « {self.model} » n'est pas installé. "
                    f"Installez-le avec : ollama pull {self.model}")
            raise OllamaError(f"Ollama a renvoyé une erreur {response.status_code} : {detail}")
        return response.json()

    def list_models(self) -> list[str]:
        data = self._request("GET", "/api/tags", timeout=5)
        return sorted(m.get("name", "") for m in data.get("models", []) if m.get("name"))

    def status(self) -> dict:
        try:
            models = self.list_models()
        except OllamaError as exc:
            return {"available": False, "models": [], "error": str(exc),
                    "url": self.base_url, "model": self.model}
        installed = self.model in models or f"{self.model}:latest" in models
        return {"available": True, "models": models, "model": self.model,
                "model_installed": installed, "url": self.base_url}

    def complete_json(self, system: str, user: str, schema: dict | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,
            "format": schema or "json",
            "options": {"temperature": 0.2, "num_ctx": 8192},
        }
        data = self._request("POST", "/api/chat", json=payload)
        return (data.get("message") or {}).get("content", "")
