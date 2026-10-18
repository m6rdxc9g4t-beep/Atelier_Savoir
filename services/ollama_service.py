"""Communication avec l'API Ollama locale et génération des flashcards.

Ollama est interrogé via /api/chat avec une sortie structurée (paramètre
`format` = schéma JSON). Le modèle doit renvoyer :

    {"flashcards": [{"question": "...", "answer": "...", "type": "definition"}]}

Le parseur accepte aussi une liste nue `[{"question": ..., "answer": ...}]`
et corrige les antislashs LaTeX mal échappés (\\frac, \\sigma…), fréquents
avec les petits modèles.
"""
import json
import math
import re

import requests

from services.text_extraction import chunk_text

CARD_TYPES = ("definition", "formule", "theoreme", "notion")

FLASHCARD_SCHEMA = {
    "type": "object",
    "properties": {
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "type": {"type": "string", "enum": list(CARD_TYPES)},
                },
                "required": ["question", "answer", "type"],
            },
        }
    },
    "required": ["flashcards"],
}

SYSTEM_PROMPT = """Tu es un assistant pédagogique qui transforme un extrait de cours en flashcards de révision.

RÈGLES STRICTES :
1. Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, de la forme :
   {"flashcards": [{"question": "...", "answer": "...", "type": "definition"}]}
2. "type" vaut exactement l'une de ces valeurs :
   - "definition" : définition d'un terme ;
   - "formule"    : formule ou relation mathématique, physique, chimique ;
   - "theoreme"   : théorème, loi, propriété (énoncé ET hypothèses) ;
   - "notion"     : idée clé, date, mécanisme, méthode.
3. Utilise UNIQUEMENT les informations présentes dans l'extrait. N'invente rien, ne complète pas avec tes connaissances.
4. Une carte = une seule idée. Question courte et précise ; réponse complète, exacte et compréhensible sans le cours.
5. Écris les formules en LaTeX : $...$ en ligne, $$...$$ pour une formule isolée. Dans le JSON, double chaque antislash : "$\\\\frac{a}{b}$".
6. Pour une formule, la question demande la formule (ou ce qu'elle exprime) ; la réponse donne la formule et la signification de chaque symbole.
7. Rédige dans la langue de l'extrait.
8. Pas de doublons. Au maximum {max_cards} cartes, en privilégiant définitions, formules et théorèmes.
9. Si l'extrait ne contient rien à mémoriser, renvoie {"flashcards": []}."""

USER_TEMPLATE = """Cours : {title}
Extrait {index}/{total} :
\"\"\"
{text}
\"\"\"

Génère au maximum {max_cards} flashcards à partir de cet extrait."""


class OllamaError(Exception):
    """Erreur lisible par l'utilisateur lors d'un appel à Ollama."""


class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="llama3.1", timeout=300,
                 chunk_chars=6000, session=None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.chunk_chars = chunk_chars
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

    def chat_json(self, system: str, user: str, schema: dict | None = None) -> str:
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

    # ------------------------------------------------------------ flashcards
    def generate_flashcards(self, text: str, title: str = "", max_cards: int = 15,
                            exclude_questions: set[str] | None = None) -> list[dict]:
        chunks = chunk_text(text, self.chunk_chars)
        if not chunks:
            raise OllamaError("Ce chapitre ne contient pas de texte à analyser.")
        per_chunk = max(3, math.ceil(max_cards / len(chunks)))
        seen = {q.strip().lower() for q in (exclude_questions or set())}
        cards = []
        for index, chunk in enumerate(chunks, start=1):
            prompt = USER_TEMPLATE.format(title=title or "Sans titre", index=index,
                                          total=len(chunks), text=chunk, max_cards=per_chunk)
            raw = self.chat_json(SYSTEM_PROMPT.replace("{max_cards}", str(per_chunk)),
                                 prompt, FLASHCARD_SCHEMA)
            for card in parse_flashcards(raw):
                key = card["question"].strip().lower()
                if key in seen:
                    continue
                seen.add(key)
                cards.append(card)
            if len(cards) >= max_cards:
                break
        return cards[:max_cards]


# ------------------------------------------------------------------ parsing
_INVALID_ESCAPE = re.compile(r'(?<!\\)((?:\\\\)*)\\(?![\\"/bfnrt]|u[0-9a-fA-F]{4})')
_LATEX_AFTER_NEWLINE = re.compile(
    r"\n(?=(?:abla|eq|e|ot|otin|u|ewline|eg|mid|leq|geq|subseteq)(?![a-zA-Z]))")


def _loads_lenient(raw: str):
    raw = raw.strip()
    # Retire d'éventuelles balises ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    candidates = [raw]
    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    if match and match.group(1) != raw:
        candidates.append(match.group(1))
    for candidate in candidates:
        for attempt in (candidate, _INVALID_ESCAPE.sub(r"\1\\\\", candidate)):
            try:
                return json.loads(attempt, strict=False)
            except json.JSONDecodeError:
                continue
    raise OllamaError("La réponse d'Ollama n'est pas un JSON exploitable. Relancez la génération "
                      "ou choisissez un modèle plus performant.")


def _restore_latex(value: str) -> str:
    """Répare les séquences JSON valides mais qui étaient du LaTeX (\\frac -> saut de page…)."""
    value = value.replace("\x0c", "\\f").replace("\x08", "\\b")
    value = re.sub(r"\t(?=[a-zA-Z])", r"\\t", value)
    value = re.sub(r"\r(?=[a-zA-Z])", r"\\r", value)
    if "$" in value:
        value = _LATEX_AFTER_NEWLINE.sub(r"\\n", value)
    return value.strip()


def normalize_card(item) -> dict | None:
    if not isinstance(item, dict):
        return None
    question = item.get("question") or item.get("recto") or item.get("front")
    answer = item.get("answer") or item.get("reponse") or item.get("réponse") or item.get("back")
    if not isinstance(question, str) or not isinstance(answer, str):
        return None
    question, answer = _restore_latex(question), _restore_latex(answer)
    if not question or not answer:
        return None
    card_type = str(item.get("type", "notion")).strip().lower()
    card_type = {"définition": "definition", "théorème": "theoreme", "loi": "theoreme",
                 "propriete": "theoreme", "propriété": "theoreme"}.get(card_type, card_type)
    if card_type not in CARD_TYPES:
        card_type = "notion"
    return {"question": question, "answer": answer, "type": card_type}


def parse_flashcards(raw: str) -> list[dict]:
    if not raw or not raw.strip():
        return []
    data = _loads_lenient(raw)
    if isinstance(data, dict):
        data = data.get("flashcards") or data.get("cards") or data.get("cartes") or []
    if not isinstance(data, list):
        return []
    cards = []
    for item in data:
        card = normalize_card(item)
        if card:
            cards.append(card)
    return cards
