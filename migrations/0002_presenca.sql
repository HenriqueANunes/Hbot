-- Lista de presença (v1.3.0/v1.4.0). Ver BO/presenca.py.
-- IF NOT EXISTS: as tabelas já existiam antes das migrations (criadas pelo init_db antigo).

-- Canal dos avisos e cargo da lista, por servidor (h.presenca_config)
CREATE TABLE IF NOT EXISTS presenca_config (
    cd_servidor TEXT PRIMARY KEY,
    cd_canal    TEXT NOT NULL,
    cd_cargo    TEXT NOT NULL
);

-- Um registro por usuário/servidor/dia de sessão
CREATE TABLE IF NOT EXISTS presencas (
    id               BIGSERIAL PRIMARY KEY,
    cd_servidor      TEXT NOT NULL,
    cd_user          TEXT NOT NULL,
    nome             TEXT,
    data             DATE NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('presente', 'ausente', 'pendente', 'falta')),
    motivo           TEXT,
    cd_canal_enquete TEXT,  -- mensagem da enquete da ausência (status pendente)
    cd_enquete       TEXT,
    marcado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (cd_servidor, cd_user, data)
);

-- Meses em que o rei das faltas já foi premiado (evita premiar duas vezes)
CREATE TABLE IF NOT EXISTS presenca_premiacoes (
    cd_servidor TEXT NOT NULL,
    mes         DATE NOT NULL,  -- primeiro dia do mês premiado
    PRIMARY KEY (cd_servidor, mes)
);
