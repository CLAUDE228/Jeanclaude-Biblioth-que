from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import engine, get_db, initialize_database
from routers.books import router as books_router


PROJECT_ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")
uploads_dir = Path(os.environ.get("UPLOADS_DIR", PROJECT_ROOT / "uploads"))
uploads_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="API Gestion de Bibliothèque",
    description="API REST de gestion des livres d'une bibliothèque.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(books_router)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    books = db.scalars(select(models.Book).order_by(models.Book.id)).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"books": books},
    )
