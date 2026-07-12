import os
import time

from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get('DATABASE_URL')
USER_TABLE_NAME = 'usuarios'
"""
Estrutura do banco (PostgreSQL):

- Conexão via variável de ambiente `DATABASE_URL`
  (ex.: postgresql://hbot:senha@db:5432/hbot)
- Tabela `usuarios`:
    id           BIGSERIAL PRIMARY KEY
    cd_servidor  TEXT     -- id do servidor Discord (string)
    cd_user      TEXT     -- id do usuário Discord (string)
    nome         TEXT
    qtd_mamadas  INTEGER  -- contador de mamadas
    gold         INTEGER  -- RPG
    pp           INTEGER  -- RPG
    UNIQUE (cd_servidor, cd_user)
"""


# Pool aberto explicitamente em init_db(); evita conectar no import do módulo.
pool = ConnectionPool(
    conninfo=DATABASE_URL or '',
    min_size=1,
    max_size=5,
    kwargs={'autocommit': True},
    open=False,
)


def init_db(retries: int = 10, delay: float = 3.0):
    """Abre o pool e garante o schema. Faz retry porque o Postgres pode
    ainda estar subindo quando o container do bot inicia."""
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL não definida — configure no .env / stack.')

    ultimo_erro = None
    for tentativa in range(1, retries + 1):
        try:
            pool.open()
            with pool.connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id          BIGSERIAL PRIMARY KEY,
                        cd_servidor TEXT NOT NULL,
                        cd_user     TEXT NOT NULL,
                        nome        TEXT,
                        qtd_mamadas INTEGER NOT NULL DEFAULT 0,
                        gold        INTEGER NOT NULL DEFAULT 0,
                        pp          INTEGER NOT NULL DEFAULT 0,
                        UNIQUE (cd_servidor, cd_user)
                    )
                    """
                )
            print('[Hbot] Banco pronto.')
            return
        except Exception as erro:  # noqa: BLE001 - queremos re-tentar em qualquer falha de conexão
            ultimo_erro = erro
            print(f'[Hbot] Banco indisponível (tentativa {tentativa}/{retries}): {erro}')
            time.sleep(delay)

    raise RuntimeError(f'Não foi possível conectar ao banco: {ultimo_erro}')


class Usuario():

    def __init__(self, user=None, cd_servidor=None):
        self.user = user
        self.cd_user = str(user.id)
        self.cd_servidor = str(cd_servidor)
        self.doc_id = None

        self.carregar()

    def carregar(self):
        """Garante que o usuário existe (upsert) e guarda o id da linha.
        Atualiza o nome caso tenha mudado, sem zerar os contadores."""
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO usuarios (cd_servidor, cd_user, nome)
                VALUES (%s, %s, %s)
                ON CONFLICT (cd_servidor, cd_user)
                DO UPDATE SET nome = EXCLUDED.nome
                RETURNING id
                """,
                (self.cd_servidor, self.cd_user, self.user.name),
            ).fetchone()
        self.doc_id = row[0]

    def add_mamada(self):
        with pool.connection() as conn:
            conn.execute(
                'UPDATE usuarios SET qtd_mamadas = qtd_mamadas + 1 WHERE id = %s',
                (self.doc_id,),
            )

    def get_mamadas(self):
        with pool.connection() as conn:
            row = conn.execute(
                'SELECT qtd_mamadas FROM usuarios WHERE id = %s',
                (self.doc_id,),
            ).fetchone()
        return row[0]

    def get_rank_mamadas(self):
        with pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT nome, qtd_mamadas
                FROM usuarios
                WHERE cd_servidor = %s
                ORDER BY qtd_mamadas DESC
                """,
                (self.cd_servidor,),
            ).fetchall()

        posicao = 0
        qtd_anterior = None
        response = ''
        for nome, qtd_mamadas in rows:
            if qtd_anterior != qtd_mamadas:
                posicao += 1
            response += f"{posicao}: {nome} mamou {qtd_mamadas} vezes\n"
            qtd_anterior = qtd_mamadas

        return response

    def set_gold(self, qtd_gold: int = None):
        try:
            if not qtd_gold:
                return False, 'É necessário dizer a quantidade de gold'

            with pool.connection() as conn:
                conn.execute(
                    'UPDATE usuarios SET gold = %s WHERE id = %s',
                    (qtd_gold, self.doc_id),
                )
            return True, 'Feito!'
        except Exception:
            return False, 'Erro ao setar o gold'

    def add_gold(self, qtd_gold: int = None):
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    'UPDATE usuarios SET gold = gold + %s WHERE id = %s RETURNING gold',
                    (qtd_gold, self.doc_id),
                ).fetchone()
            return True, '', row[0]
        except Exception:
            return False, 'Erro ao adicionar valor', None

    def get_gold(self):
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    'SELECT gold FROM usuarios WHERE id = %s',
                    (self.doc_id,),
                ).fetchone()
            return True, '', row[0]
        except Exception:
            return False, 'Erro ao buscar gold', None

    def set_pp(self, qtd_pp: int = None):
        try:
            if not qtd_pp:
                return False, 'É necessário dizer a quantidade de pp'

            with pool.connection() as conn:
                conn.execute(
                    'UPDATE usuarios SET pp = %s WHERE id = %s',
                    (qtd_pp, self.doc_id),
                )
            return True, 'Feito!'
        except Exception:
            return False, 'Erro ao settar pp'

    def add_pp(self, qtd_pp: int = None):
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    'UPDATE usuarios SET pp = pp + %s WHERE id = %s RETURNING pp',
                    (qtd_pp, self.doc_id),
                ).fetchone()
            return True, '', row[0]
        except Exception:
            return False, 'Erro ao settar pp', None

    def get_pp(self):
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    'SELECT pp FROM usuarios WHERE id = %s',
                    (self.doc_id,),
                ).fetchone()
            return True, '', row[0]
        except Exception:
            return False, 'Erro ao buscar pp', None