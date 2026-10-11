import asyncio
import random

import discord

import BO.claude
import BO.usuario

"""
"Mamadinha" aleatória: de vez em quando o bot interrompe alguém no chat mandando mamar.

- Sorteio por "sacola" (shuffle bag) por servidor (em DM, por canal): 10 fichas
  embaralhadas, só uma premiada. Exatamente 1 mamada a cada 10 mensagens, sem
  sequências longas sem nada. As sacolas ficam só em memória.
- A frase é gerada pelo Claude reagindo à mensagem (BO/claude.py); sem Claude
  (erro, timeout, sem token, outra geração rodando), usa a frase fixa.
"""

TAMANHO_SACOLA = 10
MAX_CHARS_MENSAGEM = 500
ESPERA_EMBED = 3  # segundos: o Discord gera a prévia de links depois da mensagem

# Instruções da mamada (vêm depois da PERSONA do BO/claude.py) — personalizar aqui.
INSTRUCOES = (
    'A piada interna do servidor é "mamar": de vez em quando você interrompe alguém e zoa a pessoa com isso. '
    'Quem mama é sempre o usuário, e quem é mamado é sempre você (o Hbot). Não precisa usar '
    'a expressão "dar uma mamadinha": vale qualquer variação (mamar, mamada, mamadinha, '
    'perguntar se não quer mamar, cobrar a mamada do dia...). \n\n'
    'Tom bem pesado de zoeira entre amigos: deve xingar, humilhar e falar palavrão à vontade. '
    'Escreva UMA frase curta (no máximo 20 palavras), informal, só em português do Brasil, que '
    'zoe o usuário com base no que ele acabou de mandar e puxe a piada de mamar. Se for um link, '
    'zoe o conteúdo do link (o vídeo, o jogo, a reunião...). Varie a estrutura e o jeito '
    '(ordem, pergunta, ironia, chantagem, troca, "castigo"). Responda só com a frase, sem aspas.'
)

_sacolas = {}
# Referências às tasks em andamento (evita que o asyncio as colete antes de terminar)
_tarefas = set()


def sortear(chave) -> bool:
    sacola = _sacolas.get(chave)
    if not sacola:
        sacola = [True] + [False] * (TAMANHO_SACOLA - 1)
        random.shuffle(sacola)
        _sacolas[chave] = sacola
    return sacola.pop()


def talvez_mandar(message):
    """Sorteia e, se for a vez, manda a mamada em segundo plano (a geração leva alguns segundos)."""
    chave = message.guild.id if message.guild else message.channel.id
    if sortear(chave):
        tarefa = asyncio.create_task(mandar(message))
        _tarefas.add(tarefa)
        tarefa.add_done_callback(_tarefas.discard)


async def mandar(message):
    async with message.channel.typing():
        texto = await gerar(message)
    if not texto:
        texto = f'Da uma mamadinha aqui {message.author.display_name}'
    await message.channel.send(texto, tts=True, allowed_mentions=discord.AllowedMentions.none())
    BO.usuario.Usuario(user=message.author, cd_servidor=message.guild.id).add_mamada()


def descrever_mensagem(message) -> str:
    """Descreve a mensagem do Discord em texto: conteúdo, anexos, figurinhas e embeds."""
    partes = []
    if message.content:
        partes.append(f'o texto "{message.content[:MAX_CHARS_MENSAGEM]}"')
    for anexo in message.attachments:
        tipo = (anexo.content_type or '').split('/')[0]
        tipo = {'image': 'uma imagem', 'video': 'um vídeo', 'audio': 'um áudio'}.get(tipo, 'um arquivo')
        partes.append(f'{tipo} ({anexo.filename})')
    for figurinha in message.stickers:
        partes.append(f'a figurinha "{figurinha.name}"')
    for embed in message.embeds:
        if not (embed.title or embed.description):
            continue
        origem = f' do {embed.provider.name}' if embed.provider and embed.provider.name else ''
        resumo = ' — '.join(t for t in (embed.title, (embed.description or '')[:200]) if t)
        partes.append(f'a prévia{origem}: "{resumo}"')
    return ' + '.join(partes) or 'uma mensagem sem texto'


async def gerar(message) -> str | None:
    """Gera a frase da mamadinha para o autor de `message`, reagindo a ela. None se falhar."""
    if not BO.claude.disponivel():
        return None

    # Link sem prévia ainda: espera o Discord gerar e busca a mensagem de novo
    if 'http' in message.content and not message.embeds:
        await asyncio.sleep(ESPERA_EMBED)
        try:
            message = await message.channel.fetch_message(message.id)
        except discord.HTTPException:
            pass

    quem = 'O bot' if message.author.bot else 'O usuário'
    prompt = f'{quem} {message.author.display_name} acabou de mandar no chat: {descrever_mensagem(message)}'
    return await BO.claude.gerar(prompt, INSTRUCOES)
