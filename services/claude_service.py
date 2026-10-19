"""Moteur Claude : génération de fiches via Claude Code, avec l'abonnement Claude.

L'application appelle le programme `claude` installé sur la machine en mode non
interactif (`claude -p`), avec une sortie JSON validée par schéma (`--json-schema`).
Aucune clé API n'est nécessaire : Claude Code utilise la connexion faite une fois
avec `claude` dans un terminal, et la consommation compte dans les limites de
l'abonnement (comme claude.ai).

Confidentialité : contrairement à Ollama, le texte du chapitre est envoyé à Anthropic.

Précautions :
- les variables ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL sont
  retirées de l'environnement du sous-processus : en mode -p, une clé API serait
  sinon utilisée à la place de l'abonnement (et facturée) ;
- aucun outil n'est autorisé (--tools "") et Claude Code est lancé depuis un dossier
  vide : il ne lit ni ne modifie aucun fichier, et ne charge pas le CLAUDE.md du projet.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from services.flashcard_generator import FLASHCARD_SCHEMA, FlashcardGenerator, GenerationError

CLAUDE_MODELS = [
    ("sonnet", "Claude Sonnet — rapide et précis (recommandé)"),
    ("opus", "Claude Opus — le plus performant, plus lent"),
    ("haiku", "Claude Haiku — le plus rapide"),
]

# Variables qui feraient payer à l'usage (API) ou détourneraient vers un autre serveur
_ENV_TO_DROP = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")

INSTRUCTION = "Génère les flashcards demandées à partir de l'extrait de cours fourni sur l'entrée standard."


class ClaudeError(GenerationError):
    """Erreur lisible par l'utilisateur lors d'un appel à Claude Code."""


def find_claude_binary() -> str | None:
    """Emplacements usuels de Claude Code (l'app lancée depuis le Finder a un PATH minimal)."""
    home = Path.home()
    candidates = [
        os.environ.get("CLAUDE_PATH"),
        shutil.which("claude"),
        str(home / ".local" / "bin" / "claude"),
        str(home / ".claude" / "local" / "claude"),
        "/opt/homebrew/bin/claude",
        "/usr/local/bin/claude",
        str(home / ".npm-global" / "bin" / "claude"),
    ]
    return next((c for c in candidates if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)


def subscription_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in _ENV_TO_DROP}
    home = Path.home()
    extra = [str(home / ".local" / "bin"), "/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


class ClaudeCodeClient(FlashcardGenerator):
    provider = "claude"
    label = "Claude"

    def __init__(self, model="sonnet", timeout=300, chunk_chars=40000, binary=None, runner=None):
        super().__init__(model, chunk_chars)
        self.timeout = timeout
        self.binary = binary or find_claude_binary()
        self._run = runner or subprocess.run  # injectable pour les tests

    # ---------------------------------------------------------------- état
    def status(self) -> dict:
        base = {"provider": self.provider, "model": self.model,
                "models": [m for m, _ in CLAUDE_MODELS]}
        if not self.binary:
            return {**base, "available": False, "installed": False,
                    "error": "Claude Code n'est pas installé sur cet ordinateur."}
        try:
            proc = self._run([self.binary, "auth", "status"], capture_output=True, text=True,
                             timeout=20, env=subscription_env(), cwd=tempfile.gettempdir())
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {**base, "available": False, "installed": True, "error": str(exc)}
        try:
            info = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            info = {}
        method = info.get("authMethod")
        if method is None:
            # Version ancienne sans JSON : on se fie au code de sortie
            method = "inconnu" if proc.returncode == 0 else "none"
        logged_in = method not in ("none",)
        result = {**base, "available": logged_in, "installed": True, "auth_method": method,
                  "subscription": method == "claude.ai"}
        if not logged_in:
            result["error"] = ("Claude Code n'est pas connecté. Ouvrez un terminal, tapez « claude » "
                               "et connectez-vous avec votre compte Claude.")
        return result

    # ------------------------------------------------------------- appel
    def complete_json(self, system: str, user: str, schema: dict | None = None) -> str:
        if not self.binary:
            raise ClaudeError(
                "Claude Code est introuvable. Installez-le (https://claude.com/claude-code), "
                "lancez « claude » une fois dans un terminal pour vous connecter, puis réessayez.")
        cmd = [
            self.binary, "-p", INSTRUCTION,
            "--output-format", "json",
            "--json-schema", json.dumps(schema or FLASHCARD_SCHEMA, ensure_ascii=False),
            "--system-prompt", system,
            "--model", self.model,
            "--tools", "",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--no-session-persistence",
        ]
        with tempfile.TemporaryDirectory(prefix="atelier-claude-") as workdir:
            try:
                proc = self._run(cmd, input=user, capture_output=True, text=True,
                                 timeout=self.timeout, env=subscription_env(), cwd=workdir)
            except subprocess.TimeoutExpired as exc:
                raise ClaudeError("Claude n'a pas répondu à temps. Réessayez, ou réduisez "
                                  "le nombre de fiches demandées.") from exc
            except OSError as exc:
                raise ClaudeError(f"Impossible de lancer Claude Code : {exc}") from exc
        return self._extract(proc)

    @staticmethod
    def _extract(proc) -> str:
        stdout = (proc.stdout or "").strip()
        try:
            payload = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            payload = None

        if not isinstance(payload, dict):
            if proc.returncode != 0:
                detail = (proc.stderr or stdout or "erreur inconnue").strip()[:400]
                raise ClaudeError(f"Claude Code a échoué : {detail}")
            return stdout  # texte brut : le parseur tolérant s'en charge

        if payload.get("is_error") or proc.returncode != 0:
            detail = str(payload.get("result") or proc.stderr or "erreur inconnue").strip()
            lowered = detail.lower()
            if "login" in lowered or "log in" in lowered or "authenticat" in lowered:
                raise ClaudeError("Claude Code n'est pas connecté : tapez « claude » dans un terminal "
                                  "et connectez-vous avec votre compte Claude.")
            if "limit" in lowered:
                raise ClaudeError("Limite d'utilisation de votre abonnement atteinte. Réessayez plus "
                                  "tard, ou générez avec Ollama en attendant.")
            raise ClaudeError(f"Claude Code a renvoyé une erreur : {detail[:400]}")

        structured = payload.get("structured_output")
        if structured is not None:
            return json.dumps(structured, ensure_ascii=False)
        return str(payload.get("result") or "")
