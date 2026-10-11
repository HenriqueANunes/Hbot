from pathlib import Path

"""
Migrations do banco: arquivos `.sql` em `migrations/`, aplicados em ordem de nome
(`0001_...`, `0002_...`) quando o bot liga.

- A tabela `schema_migrations` guarda quais já rodaram; cada uma roda uma vez só.
- Cada migration roda numa transação: se der erro, nada dela fica no banco e o bot não sobe.
- Nunca edite uma migration já aplicada em produção: crie uma nova (ex.: `0003_...sql`
  com um ALTER TABLE).
"""

PASTA = Path(__file__).resolve().parent.parent / 'migrations'
LOCK_ID = 7_310_501  # pg_advisory_lock: garante uma aplicação por vez (ex.: dois containers subindo)


def aplicar(pool):
    with pool.connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                versao      TEXT PRIMARY KEY,
                aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute('SELECT pg_advisory_lock(%s)', (LOCK_ID,))
        try:
            aplicadas = {row[0] for row in conn.execute('SELECT versao FROM schema_migrations')}
            for arquivo in sorted(PASTA.glob('*.sql')):
                if arquivo.stem in aplicadas:
                    continue
                with conn.transaction():
                    conn.execute(arquivo.read_text())
                    conn.execute('INSERT INTO schema_migrations (versao) VALUES (%s)', (arquivo.stem,))
                print(f'[Hbot] Migration aplicada: {arquivo.name}')
        finally:
            conn.execute('SELECT pg_advisory_unlock(%s)', (LOCK_ID,))
