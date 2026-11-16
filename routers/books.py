from datetime import date
from io import BytesIO
import os
from pathlib import Path
import unicodedata
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Book as BookModel
from schemas import Book, BookCreate


router = APIRouter(prefix="/books", tags=["Livres"])
UPLOAD_ROOT = Path(
    os.environ.get(
        "UPLOADS_DIR",
        Path(__file__).resolve().parent.parent / "uploads",
    )
)
BOOK_UPLOADS = UPLOAD_ROOT / "livres"
COVER_UPLOADS = UPLOAD_ROOT / "couvertures"
MAX_BOOK_SIZE = 20 * 1024 * 1024
MAX_COVER_SIZE = 5 * 1024 * 1024
BOOK_EXTENSIONS = {".pdf", ".docx", ".epub"}
COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


async def _read_upload(
    upload: UploadFile | None,
    *,
    extensions: set[str],
    max_size: int,
    kind: str,
) -> tuple[UploadFile, bytes] | None:
    if upload is None or not upload.filename:
        return None

    extension = Path(upload.filename).suffix.lower()
    if extension not in extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Format non autorisé pour {kind}.",
        )

    content = await upload.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"{kind.capitalize()} trop volumineux.",
        )

    valid_content = False
    if extension == ".pdf":
        valid_content = content.startswith(b"%PDF-")
    elif extension in {".docx", ".epub"}:
        try:
            with ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
                valid_content = (
                    {"[Content_Types].xml", "word/document.xml"} <= names
                    if extension == ".docx"
                    else "mimetype" in names
                    and archive.getinfo("mimetype").file_size == len(
                        b"application/epub+zip"
                    )
                    and archive.read("mimetype") == b"application/epub+zip"
                )
        except (BadZipFile, KeyError):
            valid_content = False
    elif extension == ".png":
        valid_content = content.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension in {".jpg", ".jpeg"}:
        valid_content = content.startswith(b"\xff\xd8\xff")
    elif extension == ".gif":
        valid_content = content.startswith((b"GIF87a", b"GIF89a"))
    elif extension == ".webp":
        valid_content = (
            len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
        )

    if not valid_content:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Le contenu du fichier {kind} ne correspond pas à son extension.",
        )
    return upload, content


def _save_upload(
    uploaded: tuple[UploadFile, bytes] | None,
    directory: Path,
) -> str | None:
    if uploaded is None:
        return None
    upload, content = uploaded
    filename = f"{uuid4().hex}{Path(upload.filename or '').suffix.lower()}"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    try:
        target.write_bytes(content)
    except OSError:
        target.unlink(missing_ok=True)
        raise
    subdirectory = "livres" if directory == BOOK_UPLOADS else "couvertures"
    return f"/uploads/{subdirectory}/{filename}"


def _remove_upload(path: str | None) -> None:
    if not path or not path.startswith("/uploads/"):
        return
    parts = Path(path).parts
    if len(parts) != 4 or parts[1] != "uploads":
        return
    if parts[2] not in {"livres", "couvertures"} or Path(parts[3]).name != parts[3]:
        return
    (UPLOAD_ROOT / parts[2] / parts[3]).unlink(missing_ok=True)


async def _read_book_uploads(
    fichier_livre: UploadFile | None,
    image_livre: UploadFile | None,
) -> tuple[tuple[UploadFile, bytes] | None, tuple[UploadFile, bytes] | None]:
    book_file = await _read_upload(
        fichier_livre,
        extensions=BOOK_EXTENSIONS,
        max_size=MAX_BOOK_SIZE,
        kind="fichier du livre",
    )
    cover_file = await _read_upload(
        image_livre,
        extensions=COVER_EXTENSIONS,
        max_size=MAX_COVER_SIZE,
        kind="image de couverture",
    )
    return book_file, cover_file


@router.post(
    "/",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
)
def create_book(book_data: BookCreate, db: Session = Depends(get_db)) -> BookModel:
    book = BookModel(**book_data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("/filters/")
def get_book_filters(db: Session = Depends(get_db)) -> dict[str, list[str] | list[int]]:
    authors = db.scalars(
        select(BookModel.auteur).distinct().where(BookModel.auteur != "")
    ).all()
    categories = db.scalars(
        select(BookModel.categorie).distinct().where(BookModel.categorie != "")
    ).all()
    years = db.scalars(select(BookModel.annee).distinct()).all()
    return {
        "auteurs": sorted(authors, key=str.casefold),
        "categories": sorted(categories, key=str.casefold),
        "annees": sorted(years, reverse=True),
    }


@router.get("/", response_model=list[Book])
def list_books(
    titre: str | None = None,
    auteur: str | None = None,
    annee: int | None = None,
    categorie: str | None = None,
    tri: str = "id",
    ordre: str = "asc",
    db: Session = Depends(get_db),
) -> list[BookModel]:
    query = select(BookModel)
    if titre and titre.strip():
        query = query.where(BookModel.titre.ilike(f"%{titre.strip()}%"))
    if auteur and auteur.strip():
        query = query.where(BookModel.auteur == auteur.strip())
    if annee is not None:
        query = query.where(BookModel.annee == annee)
    if categorie and categorie.strip():
        query = query.where(BookModel.categorie == categorie.strip())
    sortable = {
        "titre": BookModel.titre,
        "auteur": BookModel.auteur,
        "annee": BookModel.annee,
        "categorie": BookModel.categorie,
        "id": BookModel.id,
    }
    sort_column = sortable.get(tri, BookModel.id)
    ordering = sort_column.desc() if ordre == "desc" else sort_column.asc()
    return list(db.scalars(query.order_by(ordering, BookModel.id)).all())


@router.get("/{book_id}/download/", response_class=FileResponse)
def download_book_file(book_id: int, db: Session = Depends(get_db)) -> FileResponse:
    book = db.get(BookModel, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livre introuvable",
        )
    if not book.fichier_livre or not book.fichier_livre.startswith("/uploads/livres/"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun fichier numérique n'est disponible pour ce livre.",
        )

    filename = book.fichier_livre.removeprefix("/uploads/livres/")
    if not filename or Path(filename).name != filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier numérique introuvable.",
        )
    file_path = (BOOK_UPLOADS / filename).resolve()
    if file_path.parent != BOOK_UPLOADS.resolve() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier numérique introuvable.",
        )

    normalized_title = unicodedata.normalize("NFKD", book.titre)
    safe_title = "".join(
        character
        for character in normalized_title.encode("ascii", "ignore").decode("ascii")
        if character.isalnum() or character in " -_"
    ).strip()
    download_name = f"{safe_title or f'livre-{book_id}'}{file_path.suffix.lower()}"
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=download_name,
    )


@router.post("/upload/", response_model=Book, status_code=status.HTTP_201_CREATED)
async def create_book_with_uploads(
    titre: str = Form(min_length=1, max_length=200),
    auteur: str = Form(min_length=1, max_length=150),
    annee: int = Form(ge=0, le=9999),
    categorie: str = Form(min_length=1, max_length=100),
    date_publication: str | None = Form(default=None),
    description: str | None = Form(default=None, max_length=10000),
    fichier_livre: UploadFile | None = File(default=None),
    image_livre: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> BookModel:
    book_data = _book_data(
        titre, auteur, annee, categorie, date_publication, description
    )
    book_file, cover_file = await _read_book_uploads(fichier_livre, image_livre)
    saved_paths: list[str] = []
    try:
        book = BookModel(**book_data)
        for field, upload, directory in (
            ("fichier_livre", book_file, BOOK_UPLOADS),
            ("image_livre", cover_file, COVER_UPLOADS),
        ):
            saved_path = _save_upload(upload, directory)
            if saved_path:
                saved_paths.append(saved_path)
                setattr(book, field, saved_path)
        db.add(book)
        db.commit()
        db.refresh(book)
    except SQLAlchemyError:
        db.rollback()
        for path in saved_paths:
            _remove_upload(path)
        raise
    except OSError as error:
        for path in saved_paths:
            _remove_upload(path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible d'enregistrer les fichiers téléversés.",
        ) from error
    return book


def _book_data(
    titre: str,
    auteur: str,
    annee: int,
    categorie: str,
    date_publication: str | None,
    description: str | None,
) -> dict[str, object]:
    normalized_date = None
    if date_publication:
        try:
            normalized_date = date.fromisoformat(date_publication)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La date de publication est invalide.",
            ) from error
        if normalized_date.year != annee:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="L'année doit correspondre à la date de publication.",
            )
    return {
        "titre": titre.strip(),
        "auteur": auteur.strip(),
        "annee": annee,
        "categorie": categorie.strip(),
        "date_publication": normalized_date,
        "description": description.strip() if description else None,
    }


@router.put("/{book_id}/upload/", response_model=Book)
async def update_book_with_uploads(
    book_id: int,
    titre: str = Form(min_length=1, max_length=200),
    auteur: str = Form(min_length=1, max_length=150),
    annee: int = Form(ge=0, le=9999),
    categorie: str = Form(min_length=1, max_length=100),
    date_publication: str | None = Form(default=None),
    description: str | None = Form(default=None, max_length=10000),
    fichier_livre: UploadFile | None = File(default=None),
    image_livre: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> BookModel:
    book = db.get(BookModel, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livre introuvable",
        )

    book_data = _book_data(
        titre, auteur, annee, categorie, date_publication, description
    )
    book_file, cover_file = await _read_book_uploads(fichier_livre, image_livre)
    previous_paths: list[str] = []
    saved_paths: list[str] = []
    try:
        for field, upload, directory in (
            ("fichier_livre", book_file, BOOK_UPLOADS),
            ("image_livre", cover_file, COVER_UPLOADS),
        ):
            if upload:
                previous_path = getattr(book, field)
                if previous_path:
                    previous_paths.append(previous_path)
                saved_path = _save_upload(upload, directory)
                if saved_path:
                    saved_paths.append(saved_path)
                book_data[field] = saved_path
        for field, value in book_data.items():
            setattr(book, field, value)
        db.commit()
        db.refresh(book)
    except SQLAlchemyError:
        db.rollback()
        for path in saved_paths:
            _remove_upload(path)
        raise
    except OSError as error:
        for path in saved_paths:
            _remove_upload(path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible d'enregistrer les fichiers téléversés.",
        ) from error

    for path in previous_paths:
        _remove_upload(path)
    return book


@router.get("/{book_id}", response_model=Book)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookModel:
    book = db.get(BookModel, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livre introuvable",
        )
    return book


@router.put("/{book_id}")
def update_book(
    book_id: int,
    book_data: BookCreate,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    book = db.get(BookModel, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livre introuvable",
        )

    for field, value in book_data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)

    db.commit()
    return {"message": "Livre modifié avec succès"}


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    book = db.get(BookModel, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livre introuvable",
        )

    uploaded_paths = (book.fichier_livre, book.image_livre)
    db.delete(book)
    db.commit()
    for path in uploaded_paths:
        _remove_upload(path)
    return {"message": "Livre supprimé"}
