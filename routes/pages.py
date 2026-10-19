"""Vues HTML (navigation principale de la sidebar)."""
from flask import Blueprint, abort, render_template, request

import models
from services.claude_service import CLAUDE_MODELS
from services.settings_service import PROVIDERS, current_settings

pages = Blueprint("pages", __name__)


@pages.get("/")
def dashboard():
    queue = models.study_queue(limit=1)
    return render_template(
        "dashboard.html",
        stats=models.global_stats(),
        courses=models.list_courses(),
        next_card=queue[0] if queue else None,
    )


@pages.get("/courses")
def courses():
    return render_template("courses.html", courses=models.list_courses(),
                           subjects=models.list_subjects())


@pages.get("/courses/<int:course_id>")
def course_detail(course_id):
    course = models.get_course(course_id)
    if course is None:
        abort(404)
    return render_template(
        "course_detail.html",
        course=course,
        chapters=models.list_chapters(course_id, with_content=True),
        cards=models.list_flashcards(course_id=course_id),
    )


@pages.get("/flashcards/generate")
def generate():
    return render_template(
        "generate.html",
        courses=models.list_courses(),
        selected_course=request.args.get("course_id", type=int),
        selected_chapter=request.args.get("chapter_id", type=int),
        settings=current_settings(),
        providers=PROVIDERS,
        claude_models=CLAUDE_MODELS,
    )


@pages.get("/study")
def study():
    return render_template(
        "study.html",
        courses=models.list_courses(),
        selected_course=request.args.get("course_id", type=int),
        mode=request.args.get("mode", "dues"),
    )


@pages.get("/settings")
def settings():
    return render_template("settings.html", settings=current_settings(), providers=PROVIDERS,
                           claude_models=CLAUDE_MODELS)
