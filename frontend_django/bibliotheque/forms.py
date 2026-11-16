from django import forms
from django.core.validators import FileExtensionValidator


class BookForm(forms.Form):
    titre = forms.CharField(
        max_length=200,
        label="Titre du livre",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Titre du livre"}
        ),
    )
    auteur = forms.ChoiceField(
        required=False,
        label="Auteur",
        choices=(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    nouvel_auteur = forms.CharField(
        required=False,
        max_length=150,
        label="Nouvel auteur",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Saisir le nom de l'auteur"}
        ),
    )
    date_publication = forms.DateField(
        required=False,
        label="Date de publication",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    annee = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=9999,
        widget=forms.HiddenInput(),
    )
    categorie = forms.ChoiceField(
        required=False,
        label="Catégorie",
        choices=(),
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )
    nouvelle_categorie = forms.CharField(
        required=False,
        max_length=100,
        label="Nouvelle catégorie",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Saisir une nouvelle catégorie",
            }
        ),
    )
    description = forms.CharField(
        required=False,
        max_length=10000,
        label="Description",
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 4, "placeholder": "Résumé ou notes"}
        ),
    )
    fichier_livre = forms.FileField(
        required=False,
        label="Fichier du livre (PDF, DOCX ou EPUB)",
        validators=[FileExtensionValidator(["pdf", "docx", "epub"])],
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    image_livre = forms.FileField(
        required=False,
        label="Image de couverture",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "gif", "webp"])],
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": "image/*"}
        ),
    )

    def __init__(
        self,
        *args,
        authors: list[str] | None = None,
        categories: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        authors = authors or []
        categories = categories or []
        initial_author = self.initial.get("auteur")
        initial_category = self.initial.get("categorie")
        if initial_author and initial_author not in authors:
            authors.append(initial_author)
        if initial_category and initial_category not in categories:
            categories.append(initial_category)

        self.fields["auteur"].choices = [
            ("", "Choisir un auteur"),
            *((author, author) for author in authors),
            ("__new__", "＋ Saisir un nouvel auteur…"),
        ]
        self.fields["auteur"].widget.attrs.update(
            {"data-new-entry-select": "", "data-new-entry-target": "nouvel-auteur"}
        )
        self.fields["categorie"].choices = [
            ("", "Choisir une catégorie"),
            *((category, category) for category in categories),
            ("__new__", "＋ Saisir une nouvelle catégorie…"),
        ]
        self.fields["categorie"].widget.attrs.update(
            {
                "data-new-entry-select": "",
                "data-new-entry-target": "nouvelle-categorie",
            }
        )

    def clean(self):
        cleaned_data = super().clean()
        for field_name, new_field, label in (
            ("auteur", "nouvel_auteur", "auteur"),
            ("categorie", "nouvelle_categorie", "catégorie"),
        ):
            selected = cleaned_data.get(field_name)
            if selected == "__new__":
                value = cleaned_data.get(new_field, "").strip()
                if not value:
                    message = (
                        "Saisissez le nom du nouvel auteur."
                        if label == "auteur"
                        else "Saisissez le nom de la nouvelle catégorie."
                    )
                    self.add_error(new_field, message)
                else:
                    cleaned_data[field_name] = value
            elif selected:
                cleaned_data[field_name] = selected
            else:
                message = (
                    "Choisissez ou saisissez un auteur."
                    if label == "auteur"
                    else "Choisissez ou saisissez une catégorie."
                )
                self.add_error(field_name, message)

        publication_date = cleaned_data.get("date_publication")

        if publication_date:
            cleaned_data["annee"] = publication_date.year
        elif cleaned_data.get("annee") is None:
            self.add_error(
                "date_publication",
                "Indiquez la date complète de publication.",
            )
        return cleaned_data
