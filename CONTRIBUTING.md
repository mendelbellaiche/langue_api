# Contributing

Merci de contribuer à ce projet ! Voici quelques règles à suivre.

## Installation

```bash
pip install fastapi uvicorn
pip install 'pydantic[email]'
```

Copiez `.env.example` en `.env` et renseignez les variables nécessaires (notamment `JWT_SECRET_KEY`).

## Lancer le serveur en local

```bash
uvicorn main:app --reload
```

## Tests

Les tests des endpoints se trouvent dans `test_main.http` (à exécuter avec le client HTTP de votre IDE, en lançant le serveur au préalable).

## Workflow

1. Créez une branche depuis `main` pour votre changement.
2. Faites des commits clairs et atomiques.
3. Mettez à jour `CHANGELOG.md` si votre changement est notable pour les utilisateurs.
4. Ouvrez une pull request en décrivant le changement et son motif.

## Style de code

- Suivez le style déjà présent dans le code (typage, docstrings minimales, pas de commentaires superflus).
- Gardez les endpoints simples et cohérents avec l'architecture existante (FastAPI + SQLAlchemy).
