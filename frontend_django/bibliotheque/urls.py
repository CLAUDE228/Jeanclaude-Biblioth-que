from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", views.accueil, name="accueil"),
    path(
        "connexion/",
        auth_views.LoginView.as_view(
            template_name="bibliotheque/login.html",
            redirect_authenticated_user=True,
        ),
        name="connexion",
    ),
    path(
        "deconnexion/",
        auth_views.LogoutView.as_view(),
        name="deconnexion",
    ),
    path("tableau-de-bord/", views.dashboard, name="dashboard"),
    path("livres/", views.livres, name="livres"),
    path("ajouter/", views.ajouter_livre, name="ajouter"),
    path("modifier/<int:id>/", views.modifier_livre, name="modifier"),
    path("telecharger/<int:id>/", views.telecharger_livre, name="telecharger"),
    path("supprimer/<int:id>/", views.supprimer_livre, name="supprimer"),
    path("recherche/", views.livres, name="recherche"),
    path("statistiques/", views.statistiques, name="statistiques"),
    path("parametres/", views.parametres, name="parametres"),
]
