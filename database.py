"""Connexion SQLite et schéma de la base `savoir.db`.

Le schéma est versionné via `PRAGMA user_version` : pour faire évoluer la base,
ajouter une entrée dans MIGRATIONS (jamais modifier une migration existante).
"""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS courses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    subject     TEXT    NOT NULL DEFAULT '',
    description TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chapters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title           TEXT    NOT NULL,
    content         TEXT    NOT NULL DEFAULT '',
    source_type     TEXT    NOT NULL DEFAULT 'texte'
                    CHECK (source_type IN ('texte', 'md', 'txt', 'pdf')),
    source_filename TEXT,
    stored_path     TEXT,
    position        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS flashcards (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id        INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    chapter_id       INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    question         TEXT    NOT NULL,
    answer           TEXT    NOT NULL,
    card_type        TEXT    NOT NULL DEFAULT 'notion'
                     CHECK (card_type IN ('notion', 'definition', 'formule', 'theoreme')),
    origin           TEXT    NOT NULL DEFAULT 'manuel' CHECK (origin IN ('ia', 'manuel')),
    -- Répétition espacée (SM-2 simplifié)
    ease             REAL    NOT NULL DEFAULT 2.5,
    interval_days    REAL    NOT NULL DEFAULT 0,
    repetitions      INTEGER NOT NULL DEFAULT 0,
    status           TEXT    NOT NULL DEFAULT 'nouvelle'
                     CHECK (status IN ('nouvelle', 'a_revoir', 'en_cours', 'maitrisee')),
    due_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    last_reviewed_at TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    flashcard_id INTEGER NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    rating       TEXT    NOT NULL CHECK (rating IN ('a_revoir', 'correct', 'maitrise')),
    reviewed_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chapters_course   ON chapters(course_id, position);
CREATE INDEX IF NOT EXISTS idx_cards_course      ON flashcards(course_id);
CREATE INDEX IF NOT EXISTS idx_cards_chapter     ON flashcards(chapter_id);
CREATE INDEX IF NOT EXISTS idx_cards_due         ON flashcards(due_at);
CREATE INDEX IF NOT EXISTS idx_reviews_card      ON reviews(flashcard_id);
"""

# Index = numéro de version cible. Ajouter les futures migrations à la suite.
MIGRATIONS = [SCHEMA_V1]


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> sqlite3.Connection:
    """Connexion propre à la requête en cours."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def migrate(path: str) -> int:
    """Applique les migrations manquantes et renvoie la version finale."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        for target, script in enumerate(MIGRATIONS[version:], start=version + 1):
            conn.executescript(script)
            conn.execute(f"PRAGMA user_version = {target}")
            version = target
        conn.commit()
        return version
    finally:
        conn.close()


def init_app(app):
    migrate(app.config["DATABASE"])
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Crée ou met à jour la base savoir.db."""
        version = migrate(app.config["DATABASE"])
        click.echo(f"Base prête ({app.config['DATABASE']}), schéma v{version}.")
