# Gestion de bibliothèque

Application de gestion de livres avec une API FastAPI et une interface Django. FastAPI conserve les livres dans `books.db`; Django utilise sa propre base SQLite pour les comptes et les sessions.

## Installation

Depuis la racine du projet, activez l'environnement virtuel et installez les dépendances :

```powershell
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Démarrage

Lancez FastAPI depuis la racine pour conserver `books.db` au bon emplacement :

```powershell
uvicorn main:app --reload
```

Dans un second terminal :

```powershell
cd frontend_django
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001
```

Ouvrez `http://127.0.0.1:8001/`. La documentation FastAPI est disponible sur `http://127.0.0.1:8000/docs`.

## Démarrage avec Docker

Docker Compose construit et démarre les deux services. Les bases SQLite et les fichiers téléversés restent dans les dossiers du projet :

```powershell
docker compose up --build -d
```

Ouvrez `http://localhost:8001/` ; FastAPI reste accessible sur `http://localhost:8000/docs`. Pour arrêter les services sans supprimer les données :

```powershell
docker compose down
```

La clé Django Compose par défaut est réservée au développement local. Avant tout déploiement, définissez la variable `DJANGO_SECRET_KEY` avec une clé forte propre à l'environnement.

## Données de démonstration

Depuis la racine, lancez `python seed_books.py` pour ajouter jusqu'à 50 livres de démonstration. Le script peut être relancé sans créer de doublons. Ces entrées sont des métadonnées uniquement : elles ne contiennent ni fichier de livre ni couverture.

## Livres et fichiers

La liste peut être filtrée par titre, auteur, année et catégorie. Les filtres distincts sont fournis par `GET /books/filters/`. Dans les formulaires, l'auteur et la catégorie se choisissent parmi les valeurs existantes ou peuvent être saisis comme nouvelles valeurs. La suppression d'un livre demande confirmation et affiche le résultat ; en cas d'échec, elle permet de réessayer.

Les dates complètes et descriptions sont facultatives pour préserver les livres déjà enregistrés. Pour les nouvelles entrées, l'année est calculée à partir de la date de publication.

Les nouveaux livres peuvent comporter un document PDF, DOCX ou EPUB (20 Mo maximum) et une image JPG, PNG, GIF ou WEBP (5 Mo maximum). Les fichiers sont stockés sous `uploads/livres/` et `uploads/couvertures/`; la base conserve leurs chemins. Les colonnes manquantes sont ajoutées au premier démarrage de FastAPI, sans remplacer la base existante.

Un bouton de téléchargement est disponible dans les actions de chaque livre doté d'un fichier numérique. Le téléchargement passe par Django et nécessite une session connectée.

## Configuration

Pour un usage autre que local, définissez `DJANGO_SECRET_KEY` avec une clé propre à l'environnement et réglez `DJANGO_DEBUG=false`. Les hôtes autorisés peuvent être définis avec `DJANGO_ALLOWED_HOSTS`, et l'adresse FastAPI avec `API_URL`.
