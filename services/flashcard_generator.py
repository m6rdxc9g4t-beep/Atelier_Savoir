"""Logique commune de génération de flashcards, quel que soit le moteur d'IA.

Chaque moteur (Ollama en local, Claude via l'abonnement) n'implémente qu'une
méthode : `complete_json(system, user, schema)`, qui renvoie le texte JSON produit
par le modèle. Le découpage du chapitre, le prompt système strict, l'analyse
tolérante du JSON et le dédoublonnage sont partagés ici.

Format attendu du modèle :

    {"flashcards": [{"question": "...", "answer": "...", "type": "definition"}]}

Le parseur accepte aussi une liste nue `[{"question": ..., "answer": ...}]`
et corrige les antislashs LaTeX mal échappés (\\frac, \\sigma…).
"""
import json
import math
import re

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


class GenerationError(Exception):
    """Erreur lisible par l'utilisateur pendant la génération de fiches."""


class FlashcardGenerator:
    """Base des moteurs d'IA. Les sous-classes implémentent complete_json()."""

    provider = "base"
    label = "IA"

    def __init__(self, model: str, chunk_chars: int = 6000):
        self.model = model
        self.chunk_chars = chunk_chars

    def complete_json(self, system: str, user: str, schema: dict) -> str:
        raise NotImplementedError

    def chat_json(self, system: str, user: str, schema: dict | None = None) -> str:
        """Alias historique (tests, anciens appels)."""
        return self.complete_json(system, user, schema or FLASHCARD_SCHEMA)

    def generate_flashcards(self, text: str, title: str = "", max_cards: int = 15,
                            exclude_questions: set[str] | None = None) -> list[dict]:
        chunks = chunk_text(text, self.chunk_chars)
        if not chunks:
            raise GenerationError("Ce chapitre ne contient pas de texte à analyser.")
        per_chunk = max(3, math.ceil(max_cards / len(chunks)))
        seen = {q.strip().lower() for q in (exclude_questions or set())}
        cards = []
        for index, chunk in enumerate(chunks, start=1):
            prompt = USER_TEMPLATE.format(title=title or "Sans titre", index=index,
                                          total=len(chunks), text=chunk, max_cards=per_chunk)
            raw = self.complete_json(SYSTEM_PROMPT.replace("{max_cards}", str(per_chunk)),
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
    raise GenerationError("La réponse du modèle n'est pas un JSON exploitable. Relancez la génération "
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
