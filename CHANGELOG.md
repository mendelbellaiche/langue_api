# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-10

### Added
- Refresh token support: `/login` now also returns a `refresh_token`, plus new `/refresh` (rotates tokens) and `/logout` (revokes a token) endpoints.
- Translation history persisted per user and exposed via `GET /translations`, with pagination (`limit`/`offset` query params).
- Password strength policy on `/register` (minimum length, upper/lowercase, digit, special character).
- Rate limiting (5-10 requests/minute per IP) on `/register`, `/login`, and `/refresh`.
- In-memory caching of `/languages` (static list, previously re-fetched on every call).
- `Dockerfile` and `.dockerignore` for containerized deployment.
- `requirements.txt`, `CONTRIBUTING.md`, `VERSION` file.

### Changed
- Project split from a single `main.py` into `security.py`, `limiter.py`, and `routers/` (`auth.py`, `translate.py`) for maintainability.
- Access token lifetime reduced from 60 to 15 minutes (mitigated by refresh tokens).
- `GET /translations` response format changed from a raw list to `{"total", "limit", "offset", "items"}`.
- `/translate` error handling now distinguishes invalid input (400), provider rate limiting (429), and provider/server errors (502) instead of a generic 400 for all failures.
- Active refresh tokens capped at 5 per user; older ones are revoked automatically when the limit is exceeded.

### Fixed
- Deprecated `datetime.utcnow()` calls replaced with timezone-aware equivalents.

## [1.0.0] - 2026-08-10

### Added
- User registration and login endpoints (`/register`, `/login`) with JWT-based authentication.
- Text translation endpoint (`/translate`) supporting multiple target languages.
- Supported languages listing endpoint (`/languages`).
- API version endpoint (`/version`).
