"""Planification des révisions (algorithme SM-2 simplifié).

Les trois boutons de l'écran de révision correspondent à une note SM-2 :
    « À revoir »  -> 1 : la carte revient dans 10 minutes, facilité en baisse
    « Correct »   -> 3 : intervalle allongé normalement
    « Maîtrisé »  -> 5 : intervalle allongé avec bonus
Une carte est considérée « maîtrisée » dès que son intervalle atteint
MASTERED_INTERVAL_DAYS.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

RATINGS = {"a_revoir": 1, "correct": 3, "maitrise": 5}
MIN_EASE = 1.3
RELEARN_MINUTES = 10
MASTERED_INTERVAL_DAYS = 10
EASY_BONUS = 1.3
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # identique à datetime('now') de SQLite (UTC)


@dataclass
class Schedule:
    ease: float
    interval_days: float
    repetitions: int
    status: str
    due_at: str


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_db(dt: datetime) -> str:
    return dt.strftime(DATE_FORMAT)


def schedule(ease: float, interval_days: float, repetitions: int, rating: str,
             now: datetime | None = None) -> Schedule:
    if rating not in RATINGS:
        raise ValueError(f"Note inconnue : {rating!r}")
    now = now or utcnow()
    q = RATINGS[rating]
    new_ease = max(MIN_EASE, ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))

    if rating == "a_revoir":
        return Schedule(new_ease, 0.0, 0, "a_revoir",
                        to_db(now + timedelta(minutes=RELEARN_MINUTES)))

    reps = repetitions + 1
    if reps == 1:
        interval = 1.0 if rating == "correct" else 4.0
    elif reps == 2:
        interval = 3.0 if rating == "correct" else 10.0
    else:
        interval = max(1.0, interval_days) * new_ease
        if rating == "maitrise":
            interval *= EASY_BONUS
    interval = round(interval, 2)
    status = "maitrisee" if interval >= MASTERED_INTERVAL_DAYS else "en_cours"
    return Schedule(new_ease, interval, reps, status, to_db(now + timedelta(days=interval)))
