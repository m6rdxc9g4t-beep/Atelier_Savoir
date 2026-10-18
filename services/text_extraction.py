"""Extraction et nettoyage du texte des cours importés (Markdown, TXT, PDF)."""
import io
import re
from pathlib import PurePath

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class ExtractionError(Exception):
    """Le fichier ne peut pas être converti en texte exploitable."""


SOURCE_TYPES = {"md": "md", "markdown": "md", "txt": "txt", "pdf": "pdf"}


def extension_of(filename: str) -> str:
    return PurePath(filename or "").suffix.lower().lstrip(".")


def source_type_for(filename: str) -> str | None:
    return SOURCE_TYPES.get(extension_of(filename))


def extract_text(filename: str, data: bytes) -> str:
    kind = source_type_for(filename)
    if kind is None:
        raise ExtractionError(
            f"Format non pris en charge : « {extension_of(filename) or 'sans extension'} ». "
            "Importez un fichier .md, .txt ou .pdf.")
    if not data:
        raise ExtractionError("Le fichier est vide.")
    text = _extract_pdf(data) if kind == "pdf" else _decode(data)
    text = clean_text(text, from_pdf=(kind == "pdf"))
    if not text.strip():
        raise ExtractionError("Aucun texte n'a pu être extrait de ce fichier.")
    return text


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                raise ExtractionError("Ce PDF est protégé par un mot de passe.") from exc
        pages = [(page.extract_text() or "") for page in reader.pages]
    except PdfReadError as exc:
        raise ExtractionError(f"PDF illisible : {exc}") from exc
    text = "\n\n".join(p.strip() for p in pages if p.strip())
    if not text:
        raise ExtractionError(
            "Ce PDF ne contient pas de texte sélectionnable (document scanné ?). "
            "Passez-le d'abord dans un outil d'OCR, puis réimportez-le.")
    return text


def clean_text(text: str, from_pdf: bool = False) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace(" ", " ")
    if from_pdf:
        # Mots coupés en fin de ligne : « défini-\ntion » -> « définition »
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 6000) -> list[str]:
    """Découpe le texte en blocs ≤ max_chars, en respectant les paragraphes.

    Les blocs de formules $$…$$ ne sont jamais coupés en deux.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = _paragraphs(text)
    chunks, current = [], ""
    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long(para, max_chars))
            continue
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) > max_chars:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _paragraphs(text: str) -> list[str]:
    raw = re.split(r"\n\s*\n", text)
    merged, buffer = [], None
    for para in raw:
        if buffer is not None:
            buffer += "\n\n" + para
            if para.count("$$") % 2 == 1:
                merged.append(buffer)
                buffer = None
            continue
        if para.count("$$") % 2 == 1:
            buffer = para
        else:
            merged.append(para)
    if buffer is not None:
        merged.append(buffer)
    return [p.strip() for p in merged if p.strip()]


def _split_long(para: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?;:])\s+", para)
    parts, current = [], ""
    for sentence in sentences:
        while len(sentence) > max_chars:
            if current:
                parts.append(current)
                current = ""
            parts.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        candidate = f"{current} {sentence}".strip()
        if len(candidate) > max_chars:
            parts.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts
