from datetime import date

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titre: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    auteur: Mapped[str] = mapped_column(String(150), nullable=False)
    annee: Mapped[int] = mapped_column(Integer, nullable=False)
    categorie: Mapped[str] = mapped_column(String(100), nullable=False)
    date_publication: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    fichier_livre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_livre: Mapped[str | None] = mapped_column(String(255), nullable=True)
