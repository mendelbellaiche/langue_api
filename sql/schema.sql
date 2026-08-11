CREATE DATABASE IF NOT EXISTS langue_api CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE langue_api;

CREATE TABLE users (
    id INTEGER NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE INDEX ix_users_email (email)
);

CREATE TABLE refresh_tokens (
    id INTEGER NOT NULL AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    revoked BOOL NOT NULL DEFAULT FALSE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME,
    PRIMARY KEY (id),
    UNIQUE INDEX ix_refresh_tokens_token_hash (token_hash),
    INDEX ix_refresh_tokens_user_id (user_id),
    CONSTRAINT fk_refresh_tokens_user_id FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE translations (
    id INTEGER NOT NULL AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    source_lang VARCHAR(10) NOT NULL,
    target_lang VARCHAR(10) NOT NULL,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    created_at DATETIME,
    PRIMARY KEY (id),
    INDEX ix_translations_user_id (user_id),
    CONSTRAINT fk_translations_user_id FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE favorites (
    id INTEGER NOT NULL AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    source_lang VARCHAR(10) NOT NULL,
    target_lang VARCHAR(10) NOT NULL,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    created_at DATETIME,
    updated_at DATETIME,
    PRIMARY KEY (id),
    INDEX ix_favorites_user_id (user_id),
    CONSTRAINT fk_favorites_user_id FOREIGN KEY (user_id) REFERENCES users (id)
);
