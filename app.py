"""Point d'entrée d'Atelier_Savoir.

Lancement :  python app.py            (http://127.0.0.1:5000)
        ou   flask --app app run --debug
"""
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import database
from config import Config
from models import CARD_TYPE_LABELS
from routes import api, pages

NAV = [
    ("pages.dashboard", "Tableau de bord", "accueil"),
    ("pages.courses", "Mes cours", "cours"),
    ("pages.generate", "Générateur IA", "ia"),
    ("pages.study", "Révision", "revision"),
    ("pages.settings", "Paramètres", "reglages"),
]

STATUS_LABELS = {
    "nouvelle": "Nouvelle",
    "a_revoir": "À revoir",
    "en_cours": "En cours",
    "maitrisee": "Maîtrisée",
}


def create_app(config_object=Config, **overrides):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config.update(overrides)
    app.json.ensure_ascii = False

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    database.init_app(app)
    app.register_blueprint(pages)
    app.register_blueprint(api)

    @app.context_processor
    def inject_globals():
        return {"nav": NAV, "card_type_labels": CARD_TYPE_LABELS,
                "status_labels": STATUS_LABELS}

    @app.template_filter("pluriel")
    def pluriel(n, singulier, pluriel_=None):
        return f"{n} {singulier if n in (0, 1) else (pluriel_ or singulier + 's')}"

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Ressource introuvable."}), 404
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
