"""Tests de bout en bout (Ollama est simulé : aucun serveur requis)."""
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from services.ollama_service import OllamaClient, OllamaError, parse_flashcards  # noqa: E402
from services.spaced_repetition import schedule  # noqa: E402
from services.text_extraction import chunk_text, clean_text  # noqa: E402

FAKE_CARDS = {"flashcards": [
    {"question": "Que relie la formule $E = mc^2$ ?",
     "answer": "L'énergie $E$, la masse $m$ et la vitesse de la lumière $c$.", "type": "formule"},
    {"question": "Définition d'un système isolé", "answer": "N'échange ni énergie ni matière.",
     "type": "definition"},
]}


class FakeOllama(OllamaClient):
    """Remplace les appels HTTP par une réponse fixe."""
    calls = []

    def complete_json(self, system, user, schema=None):
        FakeOllama.calls.append(user)
        return json.dumps(FAKE_CARDS)

    def list_models(self):
        return ["llama3.1:latest"]


@pytest.fixture()
def client(tmp_path):
    app = create_app(TestConfig, DATABASE=str(tmp_path / "test.db"),
                     UPLOAD_FOLDER=str(tmp_path / "uploads"),
                     OLLAMA_CLIENT_FACTORY=FakeOllama)
    return app.test_client()


def make_course(client, title="Physique"):
    return client.post("/api/courses", json={"title": title, "subject": "Physique"}).get_json()


def make_pdf(text):
    """Petit PDF valide contenant du texte (sans dépendance supplémentaire)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, obj in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + obj + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref))
    return out.getvalue()


# ------------------------------------------------------------------- pages
@pytest.mark.parametrize("url", ["/", "/courses", "/flashcards/generate", "/study", "/settings"])
def test_pages_vides(client, url):
    assert client.get(url).status_code == 200


def test_pages_avec_donnees(client):
    course = make_course(client)
    client.post(f"/api/courses/{course['id']}/chapters", json={"title": "Ch1", "content": "Texte"})
    for url in ["/", "/courses", f"/courses/{course['id']}", "/study", "/flashcards/generate"]:
        assert client.get(url).status_code == 200
    assert client.get("/courses/999").status_code == 404


# ---------------------------------------------------------- cours/chapitres
def test_creation_cours_validation(client):
    assert client.post("/api/courses", json={"title": "  "}).status_code == 400
    course = make_course(client)
    assert course["title"] == "Physique" and course["card_count"] == 0


def test_import_texte_markdown_pdf(client):
    cid = make_course(client)["id"]
    r = client.post(f"/api/courses/{cid}/chapters", json={"title": "Notes", "content": "Énergie"})
    assert r.status_code == 201 and r.get_json()["source_type"] == "texte"

    md = io.BytesIO("# Chapitre\n\nLa loi $F = ma$.".encode("utf-8"))
    r = client.post(f"/api/courses/{cid}/chapters", data={"file": (md, "dynamique.md")},
                    content_type="multipart/form-data")
    assert r.status_code == 201
    assert r.get_json()["title"] == "dynamique"

    pdf = io.BytesIO(make_pdf("Premier principe de la thermodynamique"))
    r = client.post(f"/api/courses/{cid}/chapters", data={"file": (pdf, "thermo.pdf"), "title": "Thermo"},
                    content_type="multipart/form-data")
    assert r.status_code == 201, r.get_json()
    chapter = client.get(f"/api/chapters/{r.get_json()['id']}").get_json()
    assert "thermodynamique" in chapter["content"]

    bad = io.BytesIO(b"x")
    r = client.post(f"/api/courses/{cid}/chapters", data={"file": (bad, "image.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 400


# ---------------------------------------------------------- génération IA
def test_generation_puis_enregistrement(client):
    cid = make_course(client)["id"]
    ch = client.post(f"/api/courses/{cid}/chapters",
                     json={"title": "Relativité", "content": "E = mc^2 ..."}).get_json()
    r = client.post(f"/api/chapters/{ch['id']}/generate", json={"max_cards": 5})
    assert r.status_code == 200
    cards = r.get_json()["cards"]
    assert len(cards) == 2 and cards[0]["type"] == "formule"

    r = client.post("/api/flashcards", json={"chapter_id": ch["id"], "origin": "ia", "cards": cards})
    assert r.status_code == 201 and r.get_json()["created"] == 2

    # Les questions déjà enregistrées ne sont plus reproposées
    r = client.post(f"/api/chapters/{ch['id']}/generate", json={})
    assert r.get_json()["cards"] == []


def test_ollama_indisponible(client, monkeypatch):
    def boom(self, *a, **k):
        raise OllamaError("Impossible de joindre Ollama")
    monkeypatch.setattr(FakeOllama, "complete_json", boom)
    cid = make_course(client)["id"]
    ch = client.post(f"/api/courses/{cid}/chapters", json={"title": "A", "content": "B"}).get_json()
    r = client.post(f"/api/chapters/{ch['id']}/generate", json={})
    assert r.status_code == 502 and "Ollama" in r.get_json()["error"]


# --------------------------------------------------------------- révision
def test_session_et_evaluation(client):
    cid = make_course(client)["id"]
    client.post("/api/flashcards", json={"course_id": cid, "cards": [
        {"question": "Q1", "answer": "R1"}, {"question": "Q2", "answer": "R2", "type": "theoreme"}]})
    session = client.get(f"/api/study/session?course_id={cid}").get_json()
    assert len(session["cards"]) == 2

    card_id = session["cards"][0]["id"]
    r = client.post(f"/api/flashcards/{card_id}/review", json={"rating": "maitrise"})
    assert r.status_code == 200 and r.get_json()["status"] == "en_cours"
    assert client.post(f"/api/flashcards/{card_id}/review", json={"rating": "bof"}).status_code == 400

    # La carte notée n'est plus due aujourd'hui
    session = client.get(f"/api/study/session?course_id={cid}").get_json()
    assert [c["id"] for c in session["cards"]] != [card_id] and len(session["cards"]) == 1
    stats = client.get("/api/stats").get_json()
    assert stats["cards"] == 2 and stats["reviewed_today"] == 1


def test_suppression_en_cascade(client):
    cid = make_course(client)["id"]
    ch = client.post(f"/api/courses/{cid}/chapters", json={"title": "A", "content": "B"}).get_json()
    client.post("/api/flashcards", json={"chapter_id": ch["id"], "cards": [{"question": "q", "answer": "r"}]})
    assert client.delete(f"/api/courses/{cid}").status_code == 200
    assert client.get("/api/flashcards").get_json() == []


def test_reglages(client):
    r = client.put("/api/settings", json={"ollama_model": "mistral", "cards_per_chapter": 99})
    assert r.get_json()["ollama_model"] == "mistral" and r.get_json()["cards_per_chapter"] == "60"
    assert client.put("/api/settings", json={"ollama_url": "localhost"}).status_code == 400


# -------------------------------------------------------------- unitaires
def test_parser_latex():
    raw = r'{"flashcards":[{"question":"Intégrale","answer":"$\int_a^b f(x)\,dx = \frac{1}{2}\theta$","type":"Formule"}]}'
    card = parse_flashcards(raw)[0]
    assert card["answer"] == r"$\int_a^b f(x)\,dx = \frac{1}{2}\theta$"
    assert card["type"] == "formule"


def test_parser_liste_et_balises():
    raw = '```json\n[{"question": "a", "answer": "b"}, {"question": "", "answer": "x"}]\n```'
    assert parse_flashcards(raw) == [{"question": "a", "answer": "b", "type": "notion"}]


def test_decoupage_respecte_formules():
    bloc = "$$\n\\int_0^1 x\\,dx\n\n= \\frac12\n$$"
    text = "\n\n".join(["Paragraphe " * 40, bloc, "Suite " * 40])
    chunks = chunk_text(text, max_chars=500)
    assert any(bloc in c for c in chunks)
    assert clean_text("défini-\ntion", from_pdf=True) == "définition"


def test_repetition_espacee():
    s = schedule(2.5, 0, 0, "a_revoir")
    assert s.status == "a_revoir" and s.repetitions == 0
    s1 = schedule(2.5, 0, 0, "maitrise")
    s2 = schedule(s1.ease, s1.interval_days, s1.repetitions, "maitrise")
    assert s1.interval_days == 4 and s2.status == "maitrisee"
