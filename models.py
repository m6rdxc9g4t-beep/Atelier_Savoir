"""Accès aux données : cours, chapitres, flashcards, révisions, réglages.

Toutes les fonctions renvoient des dict (sérialisables en JSON) ou None.
"""
from database import get_db
from services.spaced_repetition import schedule, to_db, utcnow

CARD_TYPES = ("notion", "definition", "formule", "theoreme")
CARD_TYPE_LABELS = {
    "notion": "Notion clé",
    "definition": "Définition",
    "formule": "Formule",
    "theoreme": "Théorème",
}


def _row(row):
    return dict(row) if row is not None else None


def _rows(rows):
    return [dict(r) for r in rows]


# --------------------------------------------------------------------- cours
_COURSE_STATS = """
    SELECT c.*,
        (SELECT COUNT(*) FROM chapters ch WHERE ch.course_id = c.id)           AS chapter_count,
        (SELECT COUNT(*) FROM flashcards f WHERE f.course_id = c.id)           AS card_count,
        (SELECT COUNT(*) FROM flashcards f WHERE f.course_id = c.id
            AND f.status = 'maitrisee')                                        AS mastered_count,
        (SELECT COUNT(*) FROM flashcards f WHERE f.course_id = c.id
            AND f.due_at <= datetime('now'))                                   AS due_count
    FROM courses c
"""


def list_courses():
    return _rows(get_db().execute(_COURSE_STATS + " ORDER BY c.updated_at DESC, c.id DESC"))


def get_course(course_id):
    return _row(get_db().execute(_COURSE_STATS + " WHERE c.id = ?", (course_id,)).fetchone())


def create_course(title, subject="", description=""):
    db = get_db()
    cur = db.execute(
        "INSERT INTO courses (title, subject, description) VALUES (?, ?, ?)",
        (title.strip(), subject.strip(), description.strip()),
    )
    db.commit()
    return get_course(cur.lastrowid)


def update_course(course_id, **fields):
    allowed = {k: v.strip() for k, v in fields.items()
               if k in ("title", "subject", "description") and isinstance(v, str)}
    if allowed:
        sets = ", ".join(f"{k} = ?" for k in allowed)
        db = get_db()
        db.execute(f"UPDATE courses SET {sets}, updated_at = datetime('now') WHERE id = ?",
                   (*allowed.values(), course_id))
        db.commit()
    return get_course(course_id)


def touch_course(course_id):
    get_db().execute("UPDATE courses SET updated_at = datetime('now') WHERE id = ?", (course_id,))


def delete_course(course_id):
    db = get_db()
    paths = [r["stored_path"] for r in db.execute(
        "SELECT stored_path FROM chapters WHERE course_id = ? AND stored_path IS NOT NULL",
        (course_id,))]
    deleted = db.execute("DELETE FROM courses WHERE id = ?", (course_id,)).rowcount
    db.commit()
    return deleted > 0, paths


def list_subjects():
    return [r["subject"] for r in get_db().execute(
        "SELECT DISTINCT subject FROM courses WHERE subject != '' ORDER BY subject")]


# ----------------------------------------------------------------- chapitres
_CHAPTER_COLS = """
    ch.id, ch.course_id, ch.title, ch.source_type, ch.source_filename, ch.position,
    ch.created_at, length(ch.content) AS char_count,
    (SELECT COUNT(*) FROM flashcards f WHERE f.chapter_id = ch.id) AS card_count
"""


def list_chapters(course_id, with_content=False):
    cols = _CHAPTER_COLS + (", ch.content" if with_content else "")
    return _rows(get_db().execute(
        f"SELECT {cols} FROM chapters ch WHERE ch.course_id = ? ORDER BY ch.position, ch.id",
        (course_id,)))


def get_chapter(chapter_id, with_content=True):
    cols = _CHAPTER_COLS + (", ch.content, ch.stored_path" if with_content else "")
    return _row(get_db().execute(
        f"SELECT {cols} FROM chapters ch WHERE ch.id = ?", (chapter_id,)).fetchone())


def create_chapter(course_id, title, content, source_type="texte",
                   source_filename=None, stored_path=None):
    db = get_db()
    position = db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 FROM chapters WHERE course_id = ?",
        (course_id,)).fetchone()[0]
    cur = db.execute(
        """INSERT INTO chapters (course_id, title, content, source_type, source_filename,
                                 stored_path, position)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (course_id, title.strip(), content, source_type, source_filename, stored_path, position),
    )
    touch_course(course_id)
    db.commit()
    return get_chapter(cur.lastrowid)


def delete_chapter(chapter_id):
    db = get_db()
    chapter = get_chapter(chapter_id)
    if chapter is None:
        return False, None
    db.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
    db.commit()
    return True, chapter.get("stored_path")


# ---------------------------------------------------------------- flashcards
_CARD_SELECT = """
    SELECT f.*, c.title AS course_title, ch.title AS chapter_title
    FROM flashcards f
    JOIN courses c ON c.id = f.course_id
    LEFT JOIN chapters ch ON ch.id = f.chapter_id
"""


def list_flashcards(course_id=None, chapter_id=None):
    clauses, params = [], []
    if course_id is not None:
        clauses.append("f.course_id = ?")
        params.append(course_id)
    if chapter_id is not None:
        clauses.append("f.chapter_id = ?")
        params.append(chapter_id)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return _rows(get_db().execute(_CARD_SELECT + where + " ORDER BY f.chapter_id, f.id", params))


def get_flashcard(card_id):
    return _row(get_db().execute(_CARD_SELECT + " WHERE f.id = ?", (card_id,)).fetchone())


def create_flashcards(course_id, chapter_id, cards, origin="manuel"):
    """Insère une liste de cartes {question, answer, type}. Renvoie les cartes créées."""
    db = get_db()
    ids = []
    for card in cards:
        card_type = card.get("type") if card.get("type") in CARD_TYPES else "notion"
        cur = db.execute(
            """INSERT INTO flashcards (course_id, chapter_id, question, answer, card_type, origin)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (course_id, chapter_id, card["question"].strip(), card["answer"].strip(),
             card_type, origin),
        )
        ids.append(cur.lastrowid)
    touch_course(course_id)
    db.commit()
    return [get_flashcard(i) for i in ids]


def update_flashcard(card_id, **fields):
    allowed = {}
    for key in ("question", "answer"):
        if isinstance(fields.get(key), str) and fields[key].strip():
            allowed[key] = fields[key].strip()
    if fields.get("card_type") in CARD_TYPES:
        allowed["card_type"] = fields["card_type"]
    if allowed:
        sets = ", ".join(f"{k} = ?" for k in allowed)
        db = get_db()
        db.execute(f"UPDATE flashcards SET {sets} WHERE id = ?", (*allowed.values(), card_id))
        db.commit()
    return get_flashcard(card_id)


def delete_flashcard(card_id):
    db = get_db()
    deleted = db.execute("DELETE FROM flashcards WHERE id = ?", (card_id,)).rowcount
    db.commit()
    return deleted > 0


def existing_questions(chapter_id):
    return {r["question"].strip().lower() for r in get_db().execute(
        "SELECT question FROM flashcards WHERE chapter_id = ?", (chapter_id,))}


# ------------------------------------------------------------------ révision
def study_queue(course_id=None, mode="dues", limit=30):
    """Cartes à réviser : échues d'abord (les plus en retard), puis les nouvelles.

    mode="toutes" renvoie toutes les cartes du périmètre, mélangées (révision libre).
    """
    params = []
    where = []
    if course_id is not None:
        where.append("f.course_id = ?")
        params.append(course_id)
    if mode == "toutes":
        order = "RANDOM()"
    else:
        where.append("f.due_at <= datetime('now')")
        order = "CASE f.status WHEN 'nouvelle' THEN 1 ELSE 0 END, f.due_at"
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)
    return _rows(get_db().execute(f"{_CARD_SELECT}{where_sql} ORDER BY {order} LIMIT ?", params))


def review_flashcard(card_id, rating):
    card = get_flashcard(card_id)
    if card is None:
        return None
    now = utcnow()
    plan = schedule(card["ease"], card["interval_days"], card["repetitions"], rating, now)
    db = get_db()
    db.execute(
        """UPDATE flashcards
           SET ease = ?, interval_days = ?, repetitions = ?, status = ?, due_at = ?,
               last_reviewed_at = ?
           WHERE id = ?""",
        (plan.ease, plan.interval_days, plan.repetitions, plan.status, plan.due_at,
         to_db(now), card_id),
    )
    db.execute("INSERT INTO reviews (flashcard_id, rating, reviewed_at) VALUES (?, ?, ?)",
               (card_id, rating, to_db(now)))
    db.commit()
    return get_flashcard(card_id)


def global_stats():
    db = get_db()
    row = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM courses)                                         AS courses,
            (SELECT COUNT(*) FROM chapters)                                        AS chapters,
            (SELECT COUNT(*) FROM flashcards)                                      AS cards,
            (SELECT COUNT(*) FROM flashcards WHERE status = 'maitrisee')           AS mastered,
            (SELECT COUNT(*) FROM flashcards WHERE status = 'nouvelle')            AS new_cards,
            (SELECT COUNT(*) FROM flashcards WHERE due_at <= datetime('now'))      AS due,
            (SELECT COUNT(*) FROM reviews WHERE reviewed_at >= datetime('now', 'start of day'))
                                                                                   AS reviewed_today
    """).fetchone()
    return dict(row)


# ------------------------------------------------------------------ réglages
def get_settings(defaults):
    stored = {r["key"]: r["value"] for r in get_db().execute("SELECT key, value FROM settings")}
    return {**defaults, **{k: v for k, v in stored.items() if k in defaults}}


def save_settings(values):
    db = get_db()
    for key, value in values.items():
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
    db.commit()
