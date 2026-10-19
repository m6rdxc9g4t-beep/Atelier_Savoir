"""Moteur Claude (via Claude Code et l'abonnement) — aucun appel réseau réel."""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from services.claude_service import ClaudeCodeClient, ClaudeError  # noqa: E402

CARDS = {"flashcards": [
    {"question": "Énoncez le théorème de Pythagore.",
     "answer": "Dans un triangle rectangle, $a^2 + b^2 = c^2$.", "type": "theoreme"},
]}


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class Recorder:
    """Remplace subprocess.run et mémorise les appels."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        return self.responses.pop(0)


# --------------------------------------------------------------- client
def test_sortie_structuree_et_options_de_securite(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-qui-ferait-payer")
    run = Recorder(completed(json.dumps({"type": "result", "is_error": False,
                                         "result": "", "structured_output": CARDS})))
    client = ClaudeCodeClient(model="opus", binary="/usr/bin/claude", runner=run)
    cards = client.generate_flashcards("Le théorème de Pythagore…", title="Géométrie", max_cards=5)

    assert cards == CARDS["flashcards"]
    cmd, kwargs = run.calls[0]
    assert cmd[:2] == ["/usr/bin/claude", "-p"]
    assert cmd[cmd.index("--model") + 1] == "opus"
    assert cmd[cmd.index("--tools") + 1] == ""                       # aucun outil
    assert json.loads(cmd[cmd.index("--json-schema") + 1])["required"] == ["flashcards"]
    assert "--no-session-persistence" in cmd
    assert "ANTHROPIC_API_KEY" not in kwargs["env"]                   # l'abonnement est utilisé
    assert "Pythagore" in kwargs["input"]                              # le cours passe par stdin
    assert kwargs["cwd"] != str(Path.cwd())                           # dossier vide, pas le projet


def test_repli_sur_le_texte_du_resultat():
    run = Recorder(completed(json.dumps({"is_error": False, "result": json.dumps(CARDS)})))
    client = ClaudeCodeClient(binary="/usr/bin/claude", runner=run)
    assert client.generate_flashcards("texte")[0]["type"] == "theoreme"


@pytest.mark.parametrize("message, attendu", [
    ("Not logged in · Please run /login", "pas connecté"),
    ("Claude usage limit reached", "Limite d'utilisation"),
    ("Something odd", "erreur"),
])
def test_erreurs_lisibles(message, attendu):
    run = Recorder(completed(json.dumps({"is_error": True, "result": message}), returncode=1))
    client = ClaudeCodeClient(binary="/usr/bin/claude", runner=run)
    with pytest.raises(ClaudeError, match=attendu):
        client.complete_json("s", "u")


def test_claude_absent():
    client = ClaudeCodeClient(binary=None, runner=Recorder())
    client.binary = None
    with pytest.raises(ClaudeError, match="introuvable"):
        client.complete_json("s", "u")
    assert client.status()["installed"] is False


@pytest.mark.parametrize("auth, dispo, abonnement", [
    ("claude.ai", True, True), ("api_key", True, False), ("none", False, False),
])
def test_statut_de_connexion(auth, dispo, abonnement):
    run = Recorder(completed(json.dumps({"loggedIn": auth != "none", "authMethod": auth}),
                             returncode=0 if auth != "none" else 1))
    status = ClaudeCodeClient(binary="/usr/bin/claude", runner=run).status()
    assert status["available"] is dispo and status["subscription"] is abonnement


def test_vrai_sous_processus(tmp_path, monkeypatch):
    """Faux exécutable « claude » : vérifie l'appel réel (stdin, env, JSON)."""
    fake = tmp_path / "claude"
    fake.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import json, os, sys
        assert "-p" in sys.argv and "ANTHROPIC_API_KEY" not in os.environ
        texte = sys.stdin.read()
        cartes = {{"flashcards": [{{"question": "Q sur " + texte.split()[0], "answer": "R", "type": "notion"}}]}}
        print(json.dumps({{"is_error": False, "result": "", "structured_output": cartes}}))
        """))
    fake.chmod(0o755)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    client = ClaudeCodeClient(binary=str(fake), timeout=30)
    cards = client.generate_flashcards("Thermodynamique et entropie")
    assert cards[0]["question"].startswith("Q sur")


# ------------------------------------------------------------------ API
class FakeClaude(ClaudeCodeClient):
    def __init__(self, **kwargs):
        super().__init__(binary="/usr/bin/claude", runner=Recorder(), **kwargs)

    def complete_json(self, system, user, schema=None):
        return json.dumps(CARDS)

    def status(self):
        return {"provider": "claude", "available": True, "subscription": True, "model": self.model}


@pytest.fixture()
def client(tmp_path):
    app = create_app(TestConfig, DATABASE=str(tmp_path / "t.db"), UPLOAD_FOLDER=str(tmp_path / "up"),
                     CLAUDE_CLIENT_FACTORY=FakeClaude)
    return app.test_client()


def test_generation_avec_claude(client):
    cid = client.post("/api/courses", json={"title": "Maths"}).get_json()["id"]
    ch = client.post(f"/api/courses/{cid}/chapters", json={"title": "Géométrie", "content": "…"}).get_json()
    r = client.post(f"/api/chapters/{ch['id']}/generate", json={"provider": "claude", "model": "haiku"})
    data = r.get_json()
    assert r.status_code == 200 and data["provider"] == "claude" and data["model"] == "haiku"
    assert data["cards"][0]["type"] == "theoreme"
    assert client.post(f"/api/chapters/{ch['id']}/generate", json={"provider": "gpt"}).status_code == 400


def test_moteur_par_defaut_et_statut(client):
    r = client.put("/api/settings", json={"ai_provider": "claude", "claude_model": "opus"})
    assert r.get_json()["ai_provider"] == "claude"
    assert client.put("/api/settings", json={"ai_provider": "autre"}).status_code == 400
    status = client.get("/api/claude/status").get_json()
    assert status["model"] == "opus" and status["model_choices"][0]["id"] == "sonnet"
    assert client.get("/flashcards/generate").status_code == 200
    assert client.get("/settings").status_code == 200
