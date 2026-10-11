-- Contador de mamadas e mini-RPG (gold/pp), um registro por usuário por servidor.
-- IF NOT EXISTS: a tabela já existia antes das migrations (criada pelo init_db antigo).
CREATE TABLE IF NOT EXISTS usuarios (
    id          BIGSERIAL PRIMARY KEY,
    cd_servidor TEXT NOT NULL,
    cd_user     TEXT NOT NULL,
    nome        TEXT,
    qtd_mamadas INTEGER NOT NULL DEFAULT 0,
    gold        INTEGER NOT NULL DEFAULT 0,
    pp          INTEGER NOT NULL DEFAULT 0,
    UNIQUE (cd_servidor, cd_user)
);
