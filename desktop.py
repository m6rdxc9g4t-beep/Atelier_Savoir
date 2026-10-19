"""Lanceur bureau d'Atelier Savoir (utilisé par « Atelier Savoir.app » sur macOS).

- démarre le serveur Flask en arrière-plan sur 127.0.0.1 ;
- lance Ollama s'il ne tourne pas encore ;
- ouvre l'interface dans une fenêtre native (pywebview / WebKit) ;
- arrête proprement le serveur à la fermeture de la fenêtre.

Sans pywebview (ou avec --navigateur), l'interface s'ouvre dans le navigateur par défaut.
Lancement manuel :  python desktop.py   |   python desktop.py --navigateur
"""
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from werkzeug.serving import make_server

BASE_DIR = Path(__file__).resolve().parent
APP_NAME = "Atelier Savoir"
PREFERRED_PORT = int(os.environ.get("ATELIER_PORT", "5050"))
ICON_PATH = BASE_DIR / "macos" / "icon.png"

log = logging.getLogger("atelier.desktop")


# ----------------------------------------------------------------- serveur
def find_port(preferred: int = PREFERRED_PORT) -> int:
    """Port fixe de préférence (le thème mémorisé dépend de l'origine), sinon un port libre."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return sock.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("Aucun port local disponible.")


def start_server(port: int | None = None, **overrides):
    """Démarre Flask dans un thread. Renvoie (serveur, url)."""
    sys.path.insert(0, str(BASE_DIR))
    from app import create_app

    port = port or find_port()
    server = make_server("127.0.0.1", port, create_app(**overrides), threaded=True)
    threading.Thread(target=server.serve_forever, name="flask", daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    log.info("Serveur démarré sur %s", url)
    return server, url


# ------------------------------------------------------------------ Ollama
def ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")


def ollama_running(timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{ollama_url()}/api/tags", timeout=timeout):
            return True
    except Exception:  # noqa: BLE001
        return False


def find_ollama_binary() -> str | None:
    candidates = [shutil.which("ollama"), "/opt/homebrew/bin/ollama", "/usr/local/bin/ollama",
                  "/Applications/Ollama.app/Contents/Resources/ollama"]
    return next((c for c in candidates if c and os.access(c, os.X_OK)), None)


def ensure_ollama() -> subprocess.Popen | None:
    """Lance Ollama si nécessaire. Renvoie le processus si c'est nous qui l'avons démarré."""
    if ollama_running():
        return None
    process = None
    if sys.platform == "darwin" and Path("/Applications/Ollama.app").exists():
        # L'application Ollama (icône de barre de menus) gère elle-même son serveur
        subprocess.run(["open", "-g", "-a", "Ollama"], check=False)
    else:
        binary = find_ollama_binary()
        if binary is None:
            log.warning("Ollama introuvable : la génération de fiches sera indisponible.")
            return None
        process = subprocess.Popen([binary, "serve"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(30):
        if ollama_running():
            log.info("Ollama est prêt.")
            break
        time.sleep(0.5)
    else:
        log.warning("Ollama ne répond pas encore.")
    return process


# ---------------------------------------------------------------- macOS
def brand_macos_process():
    """Nom et icône d'Atelier Savoir dans le Dock et la barre de menus (au lieu de « Python »)."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSBundle

        info = NSBundle.mainBundle().infoDictionary()
        if info is not None:
            info["CFBundleName"] = APP_NAME
            info["CFBundleDisplayName"] = APP_NAME
        if ICON_PATH.exists():
            image = NSImage.alloc().initWithContentsOfFile_(str(ICON_PATH))
            if image is not None:
                NSApplication.sharedApplication().setApplicationIconImage_(image)
    except Exception as exc:  # noqa: BLE001 — purement cosmétique
        log.debug("Personnalisation macOS ignorée : %s", exc)


def storage_dir() -> str:
    """Dossier des données du WebView (thème mémorisé…)."""
    if sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "AtelierSavoir" / "webview"
    else:
        path = BASE_DIR / "instance" / "webview"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def wait_in_dialog_or_forever():
    """Mode navigateur : garde le serveur actif jusqu'à ce que l'utilisateur le ferme."""
    if sys.platform == "darwin":
        script = (f'display dialog "{APP_NAME} est ouvert dans votre navigateur.\\n\\n'
                  'Cliquez sur Quitter pour arrêter l\'application." '
                  f'buttons {{"Quitter"}} default button 1 with title "{APP_NAME}"')
        subprocess.run(["osascript", "-e", script], check=False)
    else:
        print(f"{APP_NAME} tourne. Ctrl+C pour arrêter.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


# ------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    force_browser = "--navigateur" in argv or "--browser" in argv

    server, url = start_server()
    started = {}  # processus Ollama éventuellement lancé par nous
    threading.Thread(target=lambda: started.update(ollama=ensure_ollama()),
                     name="ollama", daemon=True).start()

    try:
        webview = None
        if not force_browser:
            try:
                import webview  # pywebview
            except ImportError:
                log.warning("pywebview absent : ouverture dans le navigateur.")
        if webview is not None:
            brand_macos_process()
            webview.create_window(APP_NAME, url, width=1280, height=860, min_size=(900, 600),
                                  background_color="#0C1624", text_select=True)
            webview.start(private_mode=False, storage_path=storage_dir())
        else:
            webbrowser.open(url)
            wait_in_dialog_or_forever()
    finally:
        server.shutdown()
        ollama_process = started.get("ollama")
        if ollama_process is not None:  # on n'arrête que l'Ollama lancé par nous
            ollama_process.terminate()
        log.info("Atelier Savoir fermé.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
