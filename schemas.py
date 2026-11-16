from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BookBase(BaseModel):
    titre: str = Field(min_length=1, max_length=200)
    auteur: str = Field(min_length=1, max_length=150)
    annee: int = Field(ge=0, le=9999)
    categorie: str = Field(min_length=1, max_length=100)
    date_publication: date | None = None
    description: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def publication_year_matches_date(self) -> "BookBase":
        if self.date_publication and self.date_publication.year != self.annee:
            raise ValueError("L'année doit correspondre à la date de publication.")
        return self


class BookCreate(BookBase):
    pass


class Book(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fichier_livre: str | None = None
    image_livre: str | None = None
