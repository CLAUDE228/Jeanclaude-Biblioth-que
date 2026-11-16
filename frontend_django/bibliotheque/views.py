from typing import Any

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render

from .forms import BookForm


API = settings.API_URL
PUBLIC_API_URL = settings.PUBLIC_API_URL
REQUEST_TIMEOUT = 10
UPLOAD_TIMEOUT = (5, 60)


def _api_error_message(error: requests.HTTPError, fallback: str) -> str:
    response = error.response
    if response is not None:
        try:
            detail: Any = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None

        if isinstance(detail, str) and detail:
            return detail
        if isinstance(detail, list):
            messages_from_api = [
                item.get("msg", "")
                for item in detail
                if isinstance(item, dict) and item.get("msg")
            ]
            if messages_from_api:
                return " ".join(messages_from_api)
    return fallback


def _fetch_books(request: HttpRequest) -> list[dict[str, Any]]:
    try:
        response = requests.get(f"{API}/books/", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        messages.error(request, "Impossible de charger les livres depuis FastAPI.")
        return []


def _fetch_filters(request: HttpRequest) -> dict[str, list[Any]]:
    try:
        response = requests.get(f"{API}/books/filters/", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        messages.error(request, "Impossible de charger les filtres depuis FastAPI.")
        return {"auteurs": [], "categories": [], "annees": []}


def _form_lists(request: HttpRequest) -> dict[str, list[Any]]:
    filters = _fetch_filters(request)
    return {
        "authors": filters.get("auteurs", []),
        "categories": filters.get("categories", []),
    }


def _form_payload(form: BookForm) -> dict[str, Any]:
    cleaned_data = form.cleaned_data
    publication_date = cleaned_data.get("date_publication")
    return {
        "titre": cleaned_data["titre"],
        "auteur": cleaned_data["auteur"],
        "annee": cleaned_data["annee"],
        "categorie": cleaned_data["categorie"],
        "date_publication": publication_date.isoformat() if publication_date else "",
        "description": cleaned_data.get("description", ""),
    }


def accueil(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "bibliotheque/index.html")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    books = _fetch_books(request)
    categories: dict[str, int] = {}
    authors = set()
    for book in books:
        category = book.get("categorie") or "Non classé"
        categories[category] = categories.get(category, 0) + 1
        if book.get("auteur"):
            authors.add(book["auteur"])
    return render(
        request,
        "bibliotheque/dashboard.html",
        {
            "books": books[:5],
            "total": len(books),
            "authors_total": len(authors),
            "categories_total": len(categories),
            "labels": list(categories),
            "valeurs": list(categories.values()),
            "api_url": PUBLIC_API_URL,
        },
    )


@login_required
def livres(request: HttpRequest) -> HttpResponse:
    filters = _fetch_filters(request)
    query = {
        "titre": request.GET.get("titre", "").strip(),
        "auteur": request.GET.get("auteur", "").strip(),
        "annee": request.GET.get("annee", "").strip(),
        "categorie": request.GET.get("categorie", "").strip(),
    }
    sort = request.GET.get("tri", "id")
    direction = request.GET.get("ordre", "asc")
    params: dict[str, str] = {"tri": sort, "ordre": direction}
    params.update({key: value for key, value in query.items() if value})
    try:
        response = requests.get(
            f"{API}/books/", params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        books = response.json()
    except requests.RequestException:
        books = []
        messages.error(request, "Impossible de contacter le serveur FastAPI.")

    return render(
        request,
        "bibliotheque/livres.html",
        {
            "books": books,
            "filters": filters,
            "query": query,
            "tri": sort,
            "ordre": direction,
            "api_url": PUBLIC_API_URL,
        },
    )


@login_required
def ajouter_livre(request: HttpRequest) -> HttpResponse:
    form_options = _form_lists(request)
    form = BookForm(
        request.POST or None,
        request.FILES or None,
        authors=form_options["authors"],
        categories=form_options["categories"],
    )
    if request.method == "POST" and form.is_valid():
        files = {
            name: form.cleaned_data[name]
            for name in ("fichier_livre", "image_livre")
            if form.cleaned_data.get(name)
        }
        try:
            response = requests.post(
                f"{API}/books/upload/",
                data=_form_payload(form),
                files=files or None,
                timeout=UPLOAD_TIMEOUT,
            )
            response.raise_for_status()
        except requests.HTTPError as error:
            messages.error(
                request,
                _api_error_message(error, "FastAPI a refusé l'ajout du livre."),
            )
        except requests.RequestException:
            messages.error(request, "Impossible d'enregistrer le livre via FastAPI.")
        else:
            messages.success(request, "Livre ajouté avec succès.")
            return redirect("livres")

    context = {"form": form, **form_options}
    return render(request, "bibliotheque/ajouter_livre.html", context)


@login_required
def modifier_livre(request: HttpRequest, id: int) -> HttpResponse:
    try:
        response = requests.get(f"{API}/books/{id}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        book = response.json()
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            messages.error(request, "Livre introuvable.")
        else:
            messages.error(
                request,
                _api_error_message(error, "Impossible de charger le livre depuis FastAPI."),
            )
        return redirect("livres")
    except requests.RequestException:
        messages.error(request, "Impossible de contacter le serveur FastAPI.")
        return redirect("livres")

    initial = {
        key: value
        for key, value in book.items()
        if key not in {"fichier_livre", "image_livre"}
    }
    form_options = _form_lists(request)
    form = BookForm(
        request.POST or None,
        request.FILES or None,
        initial=initial,
        authors=form_options["authors"],
        categories=form_options["categories"],
    )
    if request.method == "POST" and form.is_valid():
        files = {
            name: form.cleaned_data[name]
            for name in ("fichier_livre", "image_livre")
            if form.cleaned_data.get(name)
        }
        try:
            response = requests.put(
                f"{API}/books/{id}/upload/",
                data=_form_payload(form),
                files=files or None,
                timeout=UPLOAD_TIMEOUT,
            )
            response.raise_for_status()
        except requests.HTTPError as error:
            messages.error(
                request,
                _api_error_message(error, "Impossible de modifier ce livre."),
            )
        except requests.RequestException:
            messages.error(request, "Impossible de contacter le serveur FastAPI.")
        else:
            messages.success(request, "Livre modifié avec succès.")
            return redirect("livres")

    context = {
        "form": form,
        "book": book,
        "api_url": PUBLIC_API_URL,
        **form_options,
    }
    return render(request, "bibliotheque/modifier_livre.html", context)


@login_required
def telecharger_livre(request: HttpRequest, id: int) -> HttpResponse:
    try:
        response = requests.get(
            f"{API}/books/{id}/download/",
            stream=True,
            timeout=UPLOAD_TIMEOUT,
        )
        response.raise_for_status()
    except requests.HTTPError as error:
        message = _api_error_message(
            error,
            "Le fichier de ce livre n'est pas disponible au téléchargement.",
        )
        if error.response is not None and error.response.status_code == 404:
            messages.warning(request, message)
        else:
            messages.error(request, message)
        return redirect("livres")
    except requests.RequestException:
        messages.error(
            request,
            "Impossible de récupérer le fichier depuis FastAPI. Veuillez réessayer.",
        )
        return redirect("livres")

    def file_chunks():
        try:
            yield from response.iter_content(chunk_size=64 * 1024)
        finally:
            response.close()

    download = StreamingHttpResponse(
        file_chunks(),
        content_type=response.headers.get(
            "Content-Type",
            "application/octet-stream",
        ),
    )
    content_disposition = response.headers.get("Content-Disposition")
    if content_disposition:
        download["Content-Disposition"] = content_disposition
    return download


@login_required
def supprimer_livre(request: HttpRequest, id: int) -> HttpResponse:
    if request.method != "POST":
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Méthode de suppression invalide."},
                status=405,
            )
        return redirect("livres")

    try:
        response = requests.delete(f"{API}/books/{id}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.HTTPError as error:
        message = _api_error_message(error, "Impossible de supprimer ce livre.")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": message}, status=502)
        messages.error(request, message)
    except requests.RequestException:
        message = "Impossible de contacter FastAPI. Veuillez réessayer."
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": message}, status=502)
        messages.error(request, "Impossible de contacter le serveur FastAPI.")
    else:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": "Le livre a bien été supprimé."})
        messages.success(request, "Livre supprimé avec succès.")

    return redirect("livres")


@login_required
def statistiques(request: HttpRequest) -> HttpResponse:
    books = _fetch_books(request)
    categories: dict[str, int] = {}
    authors = set()
    for book in books:
        category = book.get("categorie") or "Non classé"
        categories[category] = categories.get(category, 0) + 1
        if book.get("auteur"):
            authors.add(book["auteur"])

    return render(
        request,
        "bibliotheque/statistiques.html",
        {
            "labels": list(categories),
            "valeurs": list(categories.values()),
            "total": len(books),
            "authors_total": len(authors),
            "categories_total": len(categories),
        },
    )


@login_required
def parametres(request: HttpRequest) -> HttpResponse:
    return render(request, "bibliotheque/parametres.html")
