from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from BO.usuario import pool

"""
Lista de presença das sessões de jogo (segunda e quinta).

Fluxo de um dia de sessão (horários abaixo, fuso de São Paulo):
- ABERTURA:   o bot avisa no canal configurado, mencionando o cargo.
- LEMBRETE:   menciona quem do cargo ainda não marcou nada.
- FECHAMENTO: quem do cargo não marcou presença nem ausência leva uma falta.
`/presente` vale o dia todo da sessão, até o FECHAMENTO. `/ausente` também pode ser
marcado com antecedência para qualquer sessão futura (ver ler_data()).

Ausência passa por votação: o bot abre uma enquete do Discord no canal da lista e a
ausência fica `pendente` até ela acabar — quando todos os votantes (cargo, menos quem
pediu) votarem ou no FECHAMENTO da sessão. Quem não vota conta a favor: é reprovada
se metade ou mais dos votantes votar contra (empate reprova). Reprovada com a lista ainda aberta, a
marcação some (dá pra marcar presença); com a lista fechada, vira falta.

No dia 1 de cada mês (PREMIACAO), quem teve mais faltas no mês anterior
ganha uma mamada (empate: todos os empatados). Ausência avisada não conta.

Tabelas (PostgreSQL, criadas em migrations/0002_presenca.sql):
- `presenca_config`: canal e cargo da lista, por servidor (definidos com /presenca_config)
- `presencas`: um registro por usuário/servidor/dia, status presente | ausente | pendente | falta
  (`cd_canal_enquete`/`cd_enquete`: mensagem da enquete da ausência)
- `presenca_premiacoes`: meses já premiados (evita premiar duas vezes)
"""

TZ = ZoneInfo('America/Sao_Paulo')
DIAS_SESSAO = (0, 3)  # segunda, quinta (datetime.weekday())
ABERTURA = time(20, 0, tzinfo=TZ)
LEMBRETE = time(21, 0, tzinfo=TZ)
FECHAMENTO = time(23, 0, tzinfo=TZ)
PREMIACAO = time(0, 5, tzinfo=TZ)

DIAS_SEMANA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
APELIDOS_DIA = {'seg': 0, 'segunda': 0, 'qui': 3, 'quinta': 3}
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']


def agora():
    return datetime.now(TZ)


def eh_dia_de_sessao(dia: date) -> bool:
    return dia.weekday() in DIAS_SESSAO


def lista_aberta() -> bool:
    """Hoje é dia de sessão e ainda não passou do fechamento."""
    momento = agora()
    return eh_dia_de_sessao(momento.date()) and momento.time() < FECHAMENTO.replace(tzinfo=None)


def fechamento_em(dia: date) -> datetime:
    return datetime.combine(dia, FECHAMENTO.replace(tzinfo=None), tzinfo=TZ)


def proxima_sessao(dia: date) -> date:
    """Próximo dia de sessão a partir de `dia` (inclusive)."""
    while not eh_dia_de_sessao(dia):
        dia += timedelta(days=1)
    return dia


def sessao_alvo() -> date:
    """Sessão de hoje se a lista ainda está aberta; senão, a próxima."""
    hoje = agora().date()
    return hoje if lista_aberta() else proxima_sessao(hoje + timedelta(days=1))


def ler_data(texto: str, hoje: date):
    """Lê `seg`/`segunda`/`qui`/`quinta` (a próxima ocorrência) ou `DD/MM[/AAAA]`.
    Sem ano, assume a próxima vez que a data acontece. Devolve None se não for uma data."""
    texto = texto.lower()
    if texto in APELIDOS_DIA:
        dia = hoje + timedelta(days=(APELIDOS_DIA[texto] - hoje.weekday()) % 7)
        if dia == hoje and not lista_aberta():
            dia += timedelta(days=7)
        return dia
    try:
        partes = [int(p) for p in texto.split('/')]
        if len(partes) == 3:
            return date(partes[2], partes[1], partes[0])
        if len(partes) == 2:
            dia = date(hoje.year, partes[1], partes[0])
            return dia if dia >= hoje else dia.replace(year=hoje.year + 1)
    except ValueError:
        pass
    return None


def formatar_dia(dia: date) -> str:
    return f'{DIAS_SEMANA[dia.weekday()]} {dia.strftime("%d/%m")}'


def nome_mes(mes: date) -> str:
    return f'{MESES[mes.month - 1]}/{mes.year}'


# --- config ---

def set_config(cd_servidor, cd_canal, cd_cargo):
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO presenca_config (cd_servidor, cd_canal, cd_cargo)
            VALUES (%s, %s, %s)
            ON CONFLICT (cd_servidor)
            DO UPDATE SET cd_canal = EXCLUDED.cd_canal, cd_cargo = EXCLUDED.cd_cargo
            """,
            (str(cd_servidor), str(cd_canal), str(cd_cargo)),
        )


def get_config(cd_servidor):
    """Devolve (cd_canal, cd_cargo) como int, ou None se o servidor não configurou."""
    with pool.connection() as conn:
        row = conn.execute(
            'SELECT cd_canal, cd_cargo FROM presenca_config WHERE cd_servidor = %s',
            (str(cd_servidor),),
        ).fetchone()
    return (int(row[0]), int(row[1])) if row else None


def get_configs():
    """Todos os servidores configurados: lista de (cd_servidor, cd_canal, cd_cargo) como int."""
    with pool.connection() as conn:
        rows = conn.execute('SELECT cd_servidor, cd_canal, cd_cargo FROM presenca_config').fetchall()
    return [(int(s), int(c), int(r)) for s, c, r in rows]


# --- marcação ---

def marcar(cd_servidor, user, dia: date, status, motivo=None, cd_canal_enquete=None, cd_enquete=None):
    """Marca presente/ausente/pendente no dia. Sobrescreve a marcação anterior do mesmo dia."""
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO presencas (cd_servidor, cd_user, nome, data, status, motivo, cd_canal_enquete, cd_enquete)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cd_servidor, cd_user, data)
            DO UPDATE SET nome = EXCLUDED.nome, status = EXCLUDED.status, motivo = EXCLUDED.motivo,
                          cd_canal_enquete = EXCLUDED.cd_canal_enquete, cd_enquete = EXCLUDED.cd_enquete,
                          marcado_em = now()
            """,
            (str(cd_servidor), str(user.id), user.display_name, dia, status, motivo,
             cd_canal_enquete and str(cd_canal_enquete), cd_enquete and str(cd_enquete)),
        )


def get_marcacao(cd_servidor, cd_user, dia: date):
    """Marcação de um usuário no dia: dict com status, motivo, cd_canal_enquete, cd_enquete; ou None."""
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT status, motivo, cd_canal_enquete, cd_enquete FROM presencas
            WHERE cd_servidor = %s AND cd_user = %s AND data = %s
            """,
            (str(cd_servidor), str(cd_user), dia),
        ).fetchone()
    if not row:
        return None
    return {'status': row[0], 'motivo': row[1],
            'cd_canal_enquete': row[2] and int(row[2]), 'cd_enquete': row[3] and int(row[3])}


# --- votação das ausências ---

_COLUNAS_PENDENTE = 'id, cd_servidor, cd_user, nome, data, motivo, cd_canal_enquete, cd_enquete'


def _pendente(row):
    id_, cd_servidor, cd_user, nome, data, motivo, cd_canal, cd_enquete = row
    return {'id': id_, 'cd_servidor': int(cd_servidor), 'cd_user': int(cd_user), 'nome': nome, 'data': data,
            'motivo': motivo, 'cd_canal_enquete': int(cd_canal), 'cd_enquete': int(cd_enquete)}


def get_pendentes(ate: date = None):
    """Ausências em votação; com `ate`, só as de sessões até essa data (inclusive)."""
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT {_COLUNAS_PENDENTE} FROM presencas
            WHERE status = 'pendente' AND (%s::date IS NULL OR data <= %s::date)
            """,
            (ate, ate),
        ).fetchall()
    return [_pendente(r) for r in rows]


def get_pendente_por_enquete(cd_enquete):
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_COLUNAS_PENDENTE} FROM presencas WHERE status = 'pendente' AND cd_enquete = %s",
            (str(cd_enquete),),
        ).fetchone()
    return _pendente(row) if row else None


def decidir_ausencia(id_, aprovada: bool, lista_fechada: bool) -> bool:
    """Aplica o resultado da votação. Aprovada → ausente; reprovada → falta (lista fechada) ou
    some (lista aberta). Só mexe se ainda estiver pendente: devolve False se já foi decidida."""
    with pool.connection() as conn:
        if aprovada or lista_fechada:
            row = conn.execute(
                "UPDATE presencas SET status = %s WHERE id = %s AND status = 'pendente' RETURNING 1",
                ('ausente' if aprovada else 'falta', id_),
            ).fetchone()
        else:
            row = conn.execute(
                "DELETE FROM presencas WHERE id = %s AND status = 'pendente' RETURNING 1", (id_,),
            ).fetchone()
    return row is not None


def get_marcacoes(cd_servidor, dia: date):
    """{cd_user (int): (status, motivo)} do dia."""
    with pool.connection() as conn:
        rows = conn.execute(
            'SELECT cd_user, status, motivo FROM presencas WHERE cd_servidor = %s AND data = %s',
            (str(cd_servidor), dia),
        ).fetchall()
    return {int(cd_user): (status, motivo) for cd_user, status, motivo in rows}


def registrar_faltas(cd_servidor, membros, dia: date):
    """Dá falta a quem não marcou nada no dia. Idempotente. Devolve quem levou falta agora."""
    faltosos = []
    with pool.connection() as conn:
        for membro in membros:
            row = conn.execute(
                """
                INSERT INTO presencas (cd_servidor, cd_user, nome, data, status)
                VALUES (%s, %s, %s, %s, 'falta')
                ON CONFLICT (cd_servidor, cd_user, data) DO NOTHING
                RETURNING id
                """,
                (str(cd_servidor), str(membro.id), membro.display_name, dia),
            ).fetchone()
            if row:
                faltosos.append(membro)
    return faltosos


# --- relatórios ---

def get_faltas_mes(cd_servidor, mes: date):
    """[(cd_user, nome, faltas, ausencias)] do mês, mais faltas primeiro. Só quem tem alguma."""
    inicio = mes.replace(day=1)
    fim = (inicio + timedelta(days=32)).replace(day=1)
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT cd_user,
                   (array_agg(nome ORDER BY data DESC))[1] AS nome,
                   count(*) FILTER (WHERE status = 'falta')   AS faltas,
                   count(*) FILTER (WHERE status = 'ausente') AS ausencias
            FROM presencas
            WHERE cd_servidor = %s AND data >= %s AND data < %s
            GROUP BY cd_user
            HAVING count(*) FILTER (WHERE status IN ('falta', 'ausente')) > 0
            ORDER BY faltas DESC, ausencias DESC, nome
            """,
            (str(cd_servidor), inicio, fim),
        ).fetchall()
    return [(int(cd_user), nome, faltas, ausencias) for cd_user, nome, faltas, ausencias in rows]


def ja_premiado(cd_servidor, mes: date) -> bool:
    with pool.connection() as conn:
        row = conn.execute(
            'SELECT 1 FROM presenca_premiacoes WHERE cd_servidor = %s AND mes = %s',
            (str(cd_servidor), mes.replace(day=1)),
        ).fetchone()
    return row is not None


def registrar_premiacao(cd_servidor, mes: date) -> bool:
    """Marca o mês como premiado. Devolve False se outro processo já premiou."""
    with pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO presenca_premiacoes (cd_servidor, mes) VALUES (%s, %s)
            ON CONFLICT DO NOTHING RETURNING 1
            """,
            (str(cd_servidor), mes.replace(day=1)),
        ).fetchone()
    return row is not None
