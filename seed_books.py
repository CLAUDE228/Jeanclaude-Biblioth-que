from sqlalchemy import select

from database import SessionLocal, initialize_database
from models import Book


BOOKS = [
    ("Les Misérables", "Victor Hugo", 1862, "Roman"),
    ("L'Étranger", "Albert Camus", 1942, "Roman"),
    ("Le Petit Prince", "Antoine de Saint-Exupéry", 1943, "Conte"),
    ("Germinal", "Émile Zola", 1885, "Roman"),
    ("Candide", "Voltaire", 1759, "Philosophie"),
    ("Une si longue lettre", "Mariama Bâ", 1979, "Roman"),
    ("Le Vieux Nègre et la médaille", "Ferdinand Oyono", 1956, "Roman"),
    ("L'Enfant noir", "Camara Laye", 1953, "Autobiographie"),
    ("Une saison au Congo", "Aimé Césaire", 1966, "Théâtre"),
    ("Le Rouge et le Noir", "Stendhal", 1830, "Roman"),
    ("Madame Bovary", "Gustave Flaubert", 1857, "Roman"),
    ("Notre-Dame de Paris", "Victor Hugo", 1831, "Roman"),
    ("Le Comte de Monte-Cristo", "Alexandre Dumas", 1844, "Roman"),
    ("Les Fleurs du mal", "Charles Baudelaire", 1857, "Poésie"),
    ("La Peste", "Albert Camus", 1947, "Roman"),
    ("Le Père Goriot", "Honoré de Balzac", 1835, "Roman"),
    ("Bel-Ami", "Guy de Maupassant", 1885, "Roman"),
    ("Le Horla", "Guy de Maupassant", 1887, "Nouvelle"),
    ("Voyage au bout de la nuit", "Louis-Ferdinand Céline", 1932, "Roman"),
    ("L'Amant", "Marguerite Duras", 1984, "Roman"),
    ("La Condition humaine", "André Malraux", 1933, "Roman"),
    ("Le Petit Nicolas", "René Goscinny et Jean-Jacques Sempé", 1960, "Jeunesse"),
    ("Le Seigneur des anneaux", "J. R. R. Tolkien", 1954, "Fantasy"),
    ("1984", "George Orwell", 1949, "Science-fiction"),
    ("La Ferme des animaux", "George Orwell", 1945, "Satire"),
    ("Orgueil et Préjugés", "Jane Austen", 1813, "Roman"),
    ("Jane Eyre", "Charlotte Brontë", 1847, "Roman"),
    ("Les Hauts de Hurlevent", "Emily Brontë", 1847, "Roman"),
    ("Moby-Dick", "Herman Melville", 1851, "Roman"),
    ("Gatsby le Magnifique", "F. Scott Fitzgerald", 1925, "Roman"),
    ("Ne tirez pas sur l'oiseau moqueur", "Harper Lee", 1960, "Roman"),
    ("Le Vieil Homme et la Mer", "Ernest Hemingway", 1952, "Roman"),
    ("Cent ans de solitude", "Gabriel García Márquez", 1967, "Roman"),
    ("Le Procès", "Franz Kafka", 1925, "Roman"),
    ("La Métamorphose", "Franz Kafka", 1915, "Nouvelle"),
    ("Crime et Châtiment", "Fiodor Dostoïevski", 1866, "Roman"),
    ("Guerre et Paix", "Léon Tolstoï", 1869, "Roman"),
    ("Anna Karénine", "Léon Tolstoï", 1878, "Roman"),
    ("Don Quichotte", "Miguel de Cervantès", 1605, "Roman"),
    ("La Divine Comédie", "Dante Alighieri", 1321, "Poésie"),
    ("Mémoires d'Hadrien", "Marguerite Yourcenar", 1951, "Roman historique"),
    ("Le Nom de la rose", "Umberto Eco", 1980, "Roman"),
    ("Pensées pour moi-même", "Marc Aurèle", 180, "Philosophie"),
    ("Les Contemplations", "Victor Hugo", 1856, "Poésie"),
    ("Le Cid", "Pierre Corneille", 1637, "Théâtre"),
    ("Cyrano de Bergerac", "Edmond Rostand", 1897, "Théâtre"),
    ("L'Assommoir", "Émile Zola", 1877, "Roman"),
    ("Le Deuxième Sexe", "Simone de Beauvoir", 1949, "Essai"),
    ("Les Trois Mousquetaires", "Alexandre Dumas", 1844, "Roman"),
    ("Le Tour du monde en quatre-vingts jours", "Jules Verne", 1873, "Aventure"),
]


def main() -> None:
    initialize_database()
    with SessionLocal() as db:
        existing_titles = {
            title.casefold()
            for title in db.scalars(select(Book.titre)).all()
        }
        added = 0
        for title, author, year, category in BOOKS:
            if title.casefold() in existing_titles:
                continue
            db.add(
                Book(
                    titre=title,
                    auteur=author,
                    annee=year,
                    categorie=category,
                )
            )
            existing_titles.add(title.casefold())
            added += 1
        db.commit()
    print(f"{added} livre(s) ajouté(s) sur {len(BOOKS)} proposés.")


if __name__ == "__main__":
    main()
