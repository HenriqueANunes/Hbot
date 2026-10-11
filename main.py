from discord.ext import commands, tasks
from datetime import date, timedelta
import math

import discord
import os
import asyncio
import BO.usuario
import BO.mamada
import BO.presenca
import BO.presenca_mensagens
# import aiocron

# logging.basicConfig(level=logging.INFO)

# Versão do Hbot — aumente a cada alteração no código
HBOT_VERSION = "1.5.0"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # privilegiado: necessário p/ ler message.content e comandos por prefixo

client = discord.Client(intents=intents)

client = commands.Bot(command_prefix="h.", intents=intents, help_command=None)

blackList = ['jpeg', 'jpg', 'png', 'gif']

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    # on_ready pode disparar de novo em reconexões: só inicia os loops uma vez
    for loop in (abrir_lista, lembrar_lista, fechar_lista, premiar_faltas, verificar_enquetes):
        if not loop.is_running():
            loop.start()
    await recuperar_presenca()


@client.listen()
async def on_message(message):
    if message.author == client.user:
        return

    if 'prune' in message.content.lower():
        await message.channel.send('Não pode usar esse comando lixo!!')
        await message.channel.send('Use h.del')

    if message.author == client.get_user('184405311681986560'):
        await message.channel.send('Bot lixo!')


    # Quando um usuario envia uma mensagem no chat, há uma chance de o bot mandar ele mamar
    # (1 a cada 10 mensagens, por servidor; em DM, por canal) — ver BO/mamada.py
    BO.mamada.talvez_mandar(message)

# Lista os comandos disponíveis com uma breve explicação
@client.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="Comandos do Hbot",
        description="Prefixo `h.` · `<>` = obrigatório, `[]` = opcional",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="h.help", value="Mostra esta lista de comandos.", inline=False)
    embed.add_field(name="h.version", value="Mostra a versão atual do Hbot.", inline=False)
    embed.add_field(name="h.del <n>",
                    value="Apaga as últimas `n` mensagens do canal. Requer permissão de gerenciar mensagens.", inline=False)
    embed.add_field(name="h.fbe <ext> [profundidade=100]",
                    value="Procura no histórico e posta as URLs dos anexos que terminam em `ext`. Ex.: `h.fbe pdf 50`.", inline=False)
    embed.add_field(name="h.mamadas", value="Mostra quantas mamadas você acumulou.", inline=False)
    embed.add_field(name="h.rank", value="Ranking de mamadas do servidor.", inline=False)
    embed.add_field(name="h.presente",
                    value=f"Marca presença na sessão de hoje (segunda e quinta, até as {BO.presenca.FECHAMENTO.strftime('%Hh')}).",
                    inline=False)
    embed.add_field(name="h.ausente [quando] <motivo>",
                    value="Avisa que não vai. Sem `quando`, vale a próxima sessão; com antecedência: `seg`, `qui` ou "
                          "`DD/MM`. Ex.: `h.ausente 23/10 viagem`. O cargo vota numa enquete até o fechamento: "
                          "quem não vota conta a favor; com metade ou mais contra, a ausência é cancelada "
                          "(vira falta se a lista já fechou).", inline=False)
    embed.add_field(name="h.lista", value="Mostra quem já marcou presença/ausência na sessão de hoje (ou na próxima) "
                                          "e quem falta.", inline=False)
    embed.add_field(name="h.faltas [MM/AAAA]",
                    value="Faltas e ausências do mês. No dia 1, quem mais faltou no mês anterior ganha uma mamada.",
                    inline=False)
    embed.add_field(name="h.presenca_config <#canal> <@cargo>",
                    value="Define o canal dos avisos e o cargo de quem precisa marcar. Requer permissão de gerenciar o servidor.",
                    inline=False)
    await ctx.channel.send(embed=embed)


# Mostra a versão atual do Hbot
@client.command(name="version")
async def version_command(ctx):
    await ctx.channel.send(f"Hbot v{HBOT_VERSION}")


# Comando para encontrar todos os arquivos no historico do chat
# arg1: formato do arquivo a ser procurado
# arg2: profundidade da busca
@client.command(name="fbe")
async def get_file_by_extension(ctx, arg1, arg2=100):
    print("get_file_by_extension: ", arg1, arg2)
    arg2 = int(arg2)
    async for message in ctx.channel.history(before=ctx.message.created_at,
                                             limit=arg2):
        for attachment in message.attachments:
            if attachment.filename.endswith(arg1):
                print(attachment.url)
                await ctx.send(attachment.url)


# Comando para apagar mensagens do chat
# arg1: quantidade de menssagens a serem apagadas
@client.command(name="del")
async def delete_messages(ctx, arg1: int = None):
    print("delete_messages: ", arg1)

    if arg1 == None:
        await ctx.channel.send(
            "É preciso informar a quantidade de menssagens a serem apagadas!")
        return

    arg1 = int(arg1)

    if arg1 < 0:
        await ctx.channel.send("Tem que ser um numero positivo né...")
        return

    async with ctx.channel.typing():
        async for message in ctx.channel.history(before=ctx.message.created_at,
                                                 limit=arg1):
            await message.delete()

        await ctx.message.delete()
        await ctx.channel.send(":thumbsup:")
    await asyncio.sleep(2)
    message = await ctx.channel.history(limit=1).flatten()
    await message[0].delete()


@client.command(name="mamadas")
async def get_mamadas(ctx):
    qtd_mamadas = BO.usuario.Usuario(user=ctx.author,
                                     cd_servidor=ctx.guild.id).get_mamadas()
    
    await ctx.channel.send(f'Você mamou {qtd_mamadas} vezes.')


@client.command(name="rank")
async def get_rank(ctx):
    rank_mamadas = BO.usuario.Usuario(user=ctx.author,
                                      cd_servidor=ctx.guild.id).get_rank_mamadas()
    
    await ctx.channel.send(rank_mamadas)

# --- Lista de presença (lógica de banco e horários em BO/presenca.py) ---

def get_cargo_presenca(guild):
    """(canal, cargo) configurados no servidor, ou None se faltar config ou o canal/cargo sumiu."""
    config = BO.presenca.get_config(guild.id)
    if not config:
        return None
    canal, cargo = guild.get_channel(config[0]), guild.get_role(config[1])
    return (canal, cargo) if canal and cargo else None


def membros_do_cargo(cargo):
    return sorted((m for m in cargo.members if not m.bot), key=lambda m: m.display_name.lower())


def com_frase(frase, texto):
    """Junta a frase de zoeira do Claude (pode ser None) com o texto fixo da mensagem."""
    return f'{frase}\n{texto}' if frase else texto


def grupos_lista(cargo, dia, fechada=False):
    """Membros do cargo por situação no dia: presentes, ausentes, votacao, faltas, pendentes.
    Ausentes e votacao vêm como (membro, motivo)."""
    marcacoes = BO.presenca.get_marcacoes(cargo.guild.id, dia)
    grupos = {'presentes': [], 'ausentes': [], 'votacao': [], 'faltas': [], 'pendentes': []}
    for membro in membros_do_cargo(cargo):
        status, motivo = marcacoes.get(membro.id, (None, None))
        if status == 'presente':
            grupos['presentes'].append(membro)
        elif status == 'ausente':
            grupos['ausentes'].append((membro, motivo))
        elif status == 'pendente':
            grupos['votacao'].append((membro, motivo))
        elif status == 'falta' or fechada:
            grupos['faltas'].append(membro)
        else:
            grupos['pendentes'].append(membro)
    return grupos


def texto_lista(cargo, dia, fechada=False):
    grupos = grupos_lista(cargo, dia, fechada)
    presentes = [m.display_name for m in grupos['presentes']]
    ausentes = [f'{m.display_name} ({motivo})' if motivo else m.display_name for m, motivo in grupos['ausentes']]
    votacao = [f'{m.display_name} ({motivo})' for m, motivo in grupos['votacao']]
    faltas = [m.display_name for m in grupos['faltas']]
    pendentes = [m.display_name for m in grupos['pendentes']]

    linhas = [f'📋 **Lista de presença — {BO.presenca.formatar_dia(dia)}**']
    linhas.append(f'✅ Presentes ({len(presentes)}): {", ".join(presentes) or "—"}')
    linhas.append(f'🙋 Ausentes ({len(ausentes)}): {", ".join(ausentes) or "—"}')
    if votacao:
        linhas.append(f'🗳️ Ausência em votação ({len(votacao)}): {", ".join(votacao)}')
    if fechada or faltas:
        linhas.append(f'❌ Faltas ({len(faltas)}): {", ".join(faltas) or "—"}')
    if not fechada:
        linhas.append(f'⏳ Não marcaram ({len(pendentes)}): {", ".join(pendentes) or "—"}')
    return '\n'.join(linhas)


def configs_presenca():
    """[(guild, canal, cargo)] dos servidores com a lista configurada."""
    resultado = []
    for cd_servidor, cd_canal, cd_cargo in BO.presenca.get_configs():
        guild = client.get_guild(cd_servidor)
        canal = guild and guild.get_channel(cd_canal)
        cargo = guild and guild.get_role(cd_cargo)
        if canal and cargo:
            resultado.append((guild, canal, cargo))
    return resultado


async def checar_cargo(ctx):
    """Valida se o autor está na lista. Devolve True ou responde o motivo e devolve False."""
    config = get_cargo_presenca(ctx.guild)
    if not config:
        await ctx.channel.send('A lista de presença não está configurada. Use `h.presenca_config #canal @cargo`.')
        return False
    _, cargo = config
    if cargo not in ctx.author.roles:
        await ctx.channel.send(f'Você não está na lista (cargo **{cargo.name}**).')
        return False
    return True


@client.command(name="presente")
@commands.guild_only()
async def presente(ctx):
    if not await checar_cargo(ctx):
        return
    if not BO.presenca.lista_aberta():
        hoje = BO.presenca.agora().date()
        proxima = BO.presenca.proxima_sessao(hoje + timedelta(days=1))
        if BO.presenca.eh_dia_de_sessao(hoje):
            await ctx.channel.send(f'A lista de hoje já fechou. Próxima sessão: {proxima.strftime("%d/%m")}.')
        else:
            await ctx.channel.send(f'Hoje não tem sessão. Próxima: {proxima.strftime("%d/%m")}.')
        return
    hoje = BO.presenca.agora().date()
    anterior = BO.presenca.get_marcacao(ctx.guild.id, ctx.author.id, hoje)
    BO.presenca.marcar(ctx.guild.id, ctx.author, hoje, 'presente')
    await ctx.message.add_reaction('✅')
    if anterior and anterior['status'] == 'pendente':
        await encerrar_enquete(ctx.guild, anterior['cd_canal_enquete'], anterior['cd_enquete'])
        await ctx.channel.send(f'{ctx.author.display_name} vai sim! Votação da ausência cancelada.')


@client.command(name="ausente")
@commands.guild_only()
async def ausente(ctx, *, texto: str = None):
    """`h.ausente [quando] [motivo]`: `quando` é seg/qui ou DD/MM[/AAAA]; sem ele, vale a próxima sessão."""
    if not await checar_cargo(ctx):
        return
    hoje = BO.presenca.agora().date()
    dia, motivo = None, texto
    if texto:
        primeiro, _, resto = texto.partition(' ')
        dia = BO.presenca.ler_data(primeiro, hoje)
        if dia:
            motivo = resto.strip() or None

    if dia is None:
        dia = BO.presenca.sessao_alvo()
    elif not BO.presenca.eh_dia_de_sessao(dia):
        await ctx.channel.send(f'{BO.presenca.formatar_dia(dia)} não tem sessão (só segunda e quinta).')
        return
    elif dia < hoje or (dia == hoje and not BO.presenca.lista_aberta()):
        await ctx.channel.send(f'A lista de {BO.presenca.formatar_dia(dia)} já fechou.')
        return

    quando = BO.presenca.formatar_dia(dia)
    if not motivo:
        await ctx.channel.send(f'Informe o motivo pra galera votar. Ex.: `h.ausente {dia.strftime("%d/%m")} viagem`.')
        return
    anterior = BO.presenca.get_marcacao(ctx.guild.id, ctx.author.id, dia)
    if anterior and anterior['status'] in ('ausente', 'pendente'):
        situacao = 'em votação' if anterior['status'] == 'pendente' else 'aprovada'
        await ctx.channel.send(f'Você já tem uma ausência {situacao} para {quando}.')
        return

    canal, cargo = get_cargo_presenca(ctx.guild)
    votantes = [m for m in membros_do_cargo(cargo) if m != ctx.author]
    if not votantes:  # ninguém pra votar
        BO.presenca.marcar(ctx.guild.id, ctx.author, dia, 'ausente', motivo)
        await ctx.channel.send(f'🙋 Ausência marcada para {quando} (ninguém mais no cargo pra votar).')
        return

    # Enquete do Discord: dura até o fechamento da sessão (horas inteiras, mín. 1h, máx. 32 dias)
    horas = math.ceil((BO.presenca.fechamento_em(dia) - BO.presenca.agora()).total_seconds() / 3600)
    if horas > DURACAO_MAX_ENQUETE:
        await ctx.channel.send(f'Dá pra avisar com no máximo {DURACAO_MAX_ENQUETE // 24} dias de antecedência.')
        return
    enquete = discord.Poll(question=f'{ctx.author.display_name} vai faltar {quando}: "{motivo}". Aprovam?'[:300],
                           duration=timedelta(hours=max(horas, 1)))
    enquete.add_answer(text=VOTO_APROVA, emoji='✅')
    enquete.add_answer(text=VOTO_REPROVA, emoji='❌')
    async with ctx.channel.typing():
        frase = await BO.presenca_mensagens.frase_votacao(ctx.author.display_name, motivo)
    texto = (f'🗳️ {cargo.mention} votem até {quando} às {BO.presenca.FECHAMENTO.strftime("%Hh")}. '
             f'Quem não votar conta a favor (empate reprova).')
    try:
        mensagem = await canal.send(com_frase(frase, texto), poll=enquete,
                                    allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=[cargo]))
    except discord.HTTPException as erro:
        print(f'[Hbot] Erro ao criar enquete de ausência: {erro}')
        await ctx.channel.send('Não consegui abrir a votação (o bot precisa da permissão de enviar enquetes no canal).')
        return

    BO.presenca.marcar(ctx.guild.id, ctx.author, dia, 'pendente', motivo, canal.id, mensagem.id)
    await ctx.message.add_reaction('🗳️')
    if ctx.channel != canal:
        await ctx.channel.send(f'Votação da sua ausência aberta em {canal.mention}.')


# --- Votação das ausências (enquetes do Discord) ---

VOTO_APROVA = 'Aprovo'
VOTO_REPROVA = 'Não aprovo'
DURACAO_MAX_ENQUETE = 32 * 24  # horas: limite do Discord


async def buscar_enquete(guild, cd_canal, cd_enquete):
    canal = guild.get_channel(cd_canal)
    if not canal:
        return None
    try:
        return await canal.fetch_message(cd_enquete)
    except discord.HTTPException:
        return None


async def encerrar_enquete(guild, cd_canal, cd_enquete):
    mensagem = await buscar_enquete(guild, cd_canal, cd_enquete)
    if mensagem and mensagem.poll and not mensagem.poll.is_finalized():
        try:
            await mensagem.end_poll()
        except discord.HTTPException:
            pass  # já encerrada (ex.: venceu o prazo ao mesmo tempo)
    return mensagem


async def contar_votos(guild, pendente, mensagem):
    """(contra, votaram, votantes) — só conta o voto de quem é do cargo, menos quem pediu."""
    config = get_cargo_presenca(guild)
    votantes = {m.id for m in membros_do_cargo(config[1])} - {pendente['cd_user']} if config else set()
    contra, votaram = 0, set()
    if mensagem and mensagem.poll:
        for resposta in mensagem.poll.answers:
            async for usuario in resposta.voters():
                if usuario.id in votantes:
                    votaram.add(usuario.id)
                    contra += resposta.text == VOTO_REPROVA
    return contra, votaram, votantes


async def finalizar_ausencia(pendente):
    """Encerra a enquete, aplica o resultado e avisa no canal."""
    guild = client.get_guild(pendente['cd_servidor'])
    if not guild:
        return
    mensagem = await encerrar_enquete(guild, pendente['cd_canal_enquete'], pendente['cd_enquete'])
    contra, votaram, votantes = await contar_votos(guild, pendente, mensagem)
    aprovada = contra * 2 < len(votantes)  # quem não votou conta a favor; empate reprova
    lista_fechada = BO.presenca.agora() >= BO.presenca.fechamento_em(pendente['data'])
    if not BO.presenca.decidir_ausencia(pendente['id'], aprovada, lista_fechada):
        return  # outro caminho já decidiu

    quando = BO.presenca.formatar_dia(pendente['data'])
    placar = f'{contra} de {len(votantes)} contra, {len(votaram)} votaram'
    if aprovada:
        texto = f'✅ Ausência de <@{pendente["cd_user"]}> em {quando} **aprovada** ({placar}).'
    elif lista_fechada:
        texto = f'❌ Ausência de <@{pendente["cd_user"]}> em {quando} **reprovada** ({placar}). Ficou com falta.'
    else:
        texto = (f'❌ Ausência de <@{pendente["cd_user"]}> em {quando} **reprovada** ({placar}). '
                 f'Marque `h.presente` até as {BO.presenca.FECHAMENTO.strftime("%Hh")} do dia, senão é falta.')
    canal = (mensagem and mensagem.channel) or guild.get_channel(pendente['cd_canal_enquete'])
    if canal:
        membro = guild.get_member(pendente['cd_user'])
        frase = await BO.presenca_mensagens.frase_resultado(membro.display_name if membro else pendente['nome'],
                                                            pendente['motivo'], aprovada, lista_fechada)
        await canal.send(com_frase(frase, texto), allowed_mentions=discord.AllowedMentions(
            everyone=False, roles=False, users=[discord.Object(pendente['cd_user'])]))


@client.event
async def on_raw_poll_vote_add(payload):
    """Encerra a votação assim que todos os votantes votarem."""
    pendente = BO.presenca.get_pendente_por_enquete(payload.message_id)
    if not pendente:
        return
    guild = client.get_guild(pendente['cd_servidor'])
    mensagem = guild and await buscar_enquete(guild, pendente['cd_canal_enquete'], pendente['cd_enquete'])
    if not mensagem:
        return
    _, votaram, votantes = await contar_votos(guild, pendente, mensagem)
    if votantes <= votaram:
        await finalizar_ausencia(pendente)


@tasks.loop(minutes=5)
async def verificar_enquetes():
    """Encerra as votações cujo prazo (fechamento da sessão) já passou. Também cobre o bot ter ficado fora do ar."""
    momento = BO.presenca.agora()
    for pendente in BO.presenca.get_pendentes(ate=momento.date()):
        if momento >= BO.presenca.fechamento_em(pendente['data']):
            await finalizar_ausencia(pendente)


@client.command(name="lista")
@commands.guild_only()
async def lista(ctx):
    config = get_cargo_presenca(ctx.guild)
    if not config:
        await ctx.channel.send('A lista de presença não está configurada. Use `h.presenca_config #canal @cargo`.')
        return
    # Em dia de sessão mostra a de hoje (mesmo fechada); senão, a próxima, com as ausências já avisadas
    hoje = BO.presenca.agora().date()
    dia = hoje if BO.presenca.eh_dia_de_sessao(hoje) else BO.presenca.proxima_sessao(hoje)
    await ctx.channel.send(texto_lista(config[1], dia, fechada=dia == hoje and not BO.presenca.lista_aberta()),
                           allowed_mentions=discord.AllowedMentions.none())


@client.command(name="faltas")
@commands.guild_only()
async def faltas(ctx, mes: str = None):
    if mes:
        try:
            numero, ano = mes.split('/')
            mes = date(int(ano), int(numero), 1)
        except ValueError:
            await ctx.channel.send('Use o mês no formato `MM/AAAA`. Ex.: `h.faltas 10/2026`.')
            return
    else:
        mes = BO.presenca.agora().date().replace(day=1)

    linhas = [f'📋 **Faltas de {BO.presenca.nome_mes(mes)}**']
    for posicao, (_, nome, qtd_faltas, qtd_ausencias) in enumerate(BO.presenca.get_faltas_mes(ctx.guild.id, mes), 1):
        linhas.append(f'{posicao}. {nome} — {qtd_faltas} falta(s), {qtd_ausencias} ausência(s)')
    if len(linhas) == 1:
        linhas.append('Ninguém faltou nem se ausentou. 👏')
    await ctx.channel.send('\n'.join(linhas), allowed_mentions=discord.AllowedMentions.none())


@client.command(name="presenca_config")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def presenca_config(ctx, canal: discord.TextChannel, cargo: discord.Role):
    BO.presenca.set_config(ctx.guild.id, canal.id, cargo.id)
    await ctx.channel.send(f'Feito! Avisos em {canal.mention}, lista do cargo **{cargo.name}**.',
                           allowed_mentions=discord.AllowedMentions.none())


@presenca_config.error
async def presenca_config_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.channel.send('Precisa da permissão de gerenciar o servidor.')
    else:
        await ctx.channel.send('Uso: `h.presenca_config #canal @cargo`')


@tasks.loop(time=BO.presenca.ABERTURA)
async def abrir_lista():
    if not BO.presenca.eh_dia_de_sessao(BO.presenca.agora().date()):
        return
    fechamento = BO.presenca.FECHAMENTO.strftime('%Hh')
    for _, canal, cargo in configs_presenca():
        frase = await BO.presenca_mensagens.frase_abertura(BO.presenca.agora().date())
        texto = (f'📋 {cargo.mention} Lista de presença aberta! '
                 f'Marquem `h.presente` (ou `h.ausente [motivo]`) até as {fechamento}.')
        await canal.send(com_frase(frase, texto),
                         allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=[cargo]))


@tasks.loop(time=BO.presenca.LEMBRETE)
async def lembrar_lista():
    hoje = BO.presenca.agora().date()
    if not BO.presenca.eh_dia_de_sessao(hoje):
        return
    fechamento = BO.presenca.FECHAMENTO.strftime('%Hh')
    for guild, canal, cargo in configs_presenca():
        marcacoes = BO.presenca.get_marcacoes(guild.id, hoje)
        pendentes = [m for m in membros_do_cargo(cargo) if m.id not in marcacoes]
        if pendentes:
            frase = await BO.presenca_mensagens.frase_lembrete([m.display_name for m in pendentes])
            texto = (f'⏰ {" ".join(m.mention for m in pendentes)} a lista fecha às {fechamento}! '
                     f'`h.presente` ou `h.ausente [motivo]`, senão é falta.')
            await canal.send(com_frase(frase, texto),
                             allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=pendentes))


@tasks.loop(time=BO.presenca.FECHAMENTO)
async def fechar_lista():
    hoje = BO.presenca.agora().date()
    if not BO.presenca.eh_dia_de_sessao(hoje):
        return
    for pendente in BO.presenca.get_pendentes(ate=hoje):
        await finalizar_ausencia(pendente)
    for guild, canal, cargo in configs_presenca():
        BO.presenca.registrar_faltas(guild.id, membros_do_cargo(cargo), hoje)
        grupos = grupos_lista(cargo, hoje, fechada=True)
        frase = await BO.presenca_mensagens.frase_fechamento([m.display_name for m in grupos['presentes']],
                                                             [m.display_name for m, _ in grupos['ausentes']],
                                                             [m.display_name for m in grupos['faltas']])
        await canal.send(com_frase(frase, texto_lista(cargo, hoje, fechada=True)),
                         allowed_mentions=discord.AllowedMentions.none())


@tasks.loop(time=BO.presenca.PREMIACAO)
async def premiar_faltas():
    await premiar_mes_anterior()


async def premiar_mes_anterior():
    """Quem mais faltou no mês anterior ganha uma mamada (empate: todos). Idempotente."""
    mes = (BO.presenca.agora().date().replace(day=1) - timedelta(days=1)).replace(day=1)
    for guild, canal, _ in configs_presenca():
        if BO.presenca.ja_premiado(guild.id, mes):
            continue
        ranking = BO.presenca.get_faltas_mes(guild.id, mes)
        maior = max((qtd_faltas for _, _, qtd_faltas, _ in ranking), default=0)
        if not BO.presenca.registrar_premiacao(guild.id, mes) or maior == 0:
            continue

        ganhadores, nomes, membros = [], [], []
        for cd_user, nome, qtd_faltas, _ in ranking:
            if qtd_faltas != maior:
                break
            membro = guild.get_member(cd_user)
            if membro:
                BO.usuario.Usuario(user=membro, cd_servidor=guild.id).add_mamada()
                ganhadores.append(membro.mention)
                nomes.append(membro.display_name)
                membros.append(membro)
            else:
                ganhadores.append(nome)  # saiu do servidor: só é citado
                nomes.append(nome)
        frase = await BO.presenca_mensagens.frase_rei_das_faltas(nomes, maior, BO.presenca.nome_mes(mes))
        texto = (f'🏆 Rei das faltas de {BO.presenca.nome_mes(mes)}: {", ".join(ganhadores)} '
                 f'({maior} falta(s)). {"Ganharam" if len(ganhadores) > 1 else "Ganhou"} uma mamada! 😈')
        await canal.send(com_frase(frase, texto),
                         allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=membros))


async def recuperar_presenca():
    """Recupera o que o bot perdeu se estava fora do ar no horário (ex.: deploy no horário do fechamento).
    Encerra votações vencidas, fecha a lista de hoje em silêncio e faz a premiação do mês anterior."""
    await verificar_enquetes()
    hoje = BO.presenca.agora().date()
    if BO.presenca.eh_dia_de_sessao(hoje) and not BO.presenca.lista_aberta():
        for guild, _, cargo in configs_presenca():
            BO.presenca.registrar_faltas(guild.id, membros_do_cargo(cargo), hoje)
    await premiar_mes_anterior()


BO.usuario.init_db()
client.run(os.getenv('TOKEN'))
