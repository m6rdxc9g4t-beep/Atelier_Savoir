"""Tests du lanceur bureau (sans interface graphique)."""
import socket
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import desktop  # noqa: E402


def test_port_prefere_ou_libre():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        taken = busy.getsockname()[1]
        port = desktop.find_port(taken)
    assert port != taken and port > 0


def test_serveur_en_arriere_plan(tmp_path):
    server, url = desktop.start_server(desktop.find_port(0), DATABASE=str(tmp_path / "savoir.db"),
                                       UPLOAD_FOLDER=str(tmp_path / "uploads"))
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            assert "Atelier Savoir" in response.read().decode()
    finally:
        server.shutdown()


def test_ollama_deja_lance(monkeypatch):
    monkeypatch.setattr(desktop, "ollama_running", lambda timeout=1.0: True)
    assert desktop.ensure_ollama() is None


def test_icone_presente():
    assert desktop.ICON_PATH.exists()
