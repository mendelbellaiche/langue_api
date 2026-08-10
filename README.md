# langue_api

API de traduction avec authentification JWT, construite avec FastAPI, SQLAlchemy et [deep-translator](https://github.com/nidhaloff/deep-translator).

## Fonctionnalités

- Inscription et connexion d'utilisateurs (`/register`, `/login`) avec mot de passe hashé (bcrypt) et token JWT.
- Traduction de texte vers plusieurs langues cibles (`/translate`), protégée par authentification.
- Liste des langues supportées (`/languages`).
- Version de l'API (`/version`).

## Prérequis

- Python 3.12+
- Une base de données accessible via une URL SQLAlchemy (`DATABASE_URL`)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copiez `.env.example` en `.env` et renseignez les variables :

```bash
cp .env.example .env
```

- `DATABASE_URL` : URL de connexion à la base de données (ex: `sqlite:///./app.db`)
- `JWT_SECRET_KEY` : clé secrète utilisée pour signer les tokens JWT

## Lancer le serveur

```bash
uvicorn main:app --reload
```

L'API est accessible sur `http://127.0.0.1:8000`, avec la documentation interactive sur `http://127.0.0.1:8000/docs`.

## Lancer avec Docker

```bash
docker build -t langue_api .
docker run -p 8000:8000 -e JWT_SECRET_KEY=your-secret -e DATABASE_URL=sqlite:///./app.db langue_api
```

## Tests

Les tests des endpoints se trouvent dans `test_main.http`, exécutables directement depuis le client HTTP de votre IDE (serveur lancé au préalable).

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

Voir [CHANGELOG.md](CHANGELOG.md).

## Licence

Voir [LICENSE](LICENSE).
