import asyncio
import os
import shutil
import tempfile

import discord

"""
Geração de mensagens com o Claude Code (CLI `claude`) em modo não interativo.

- Autenticação via variável de ambiente `CLAUDE_CODE_OAUTH_TOKEN`
  (gerada uma vez com `claude setup-token`; usa a assinatura, não créditos de API).
- Sem o binário ou sem o token, `gerar_mamada` devolve None e o bot usa a frase fixa.
- Só uma chamada por vez: se já tiver uma rodando, devolve None na hora
  (protege a CPU do servidor e o limite da assinatura).
"""

CLAUDE_BIN = shutil.which('claude')
MODELO = 'haiku'
TIMEOUT = 15  # segundos (sem thinking leva ~2–5 s)
MAX_CHARS_MENSAGEM = 500
MAX_CHARS_RESPOSTA = 300
ESPERA_EMBED = 3  # segundos: o Discord gera a prévia de links depois da mensagem

# Prompt fixo — personalizar aqui.
SYSTEM_PROMPT = (
    'Você é o Hbot, bot zoeiro de um servidor de Discord entre amigos. A piada interna do '
    'servidor é "mamar": de vez em quando você interrompe alguém e zoa a pessoa com isso. '
    'Quem mama é sempre o usuário, e quem é mamado é sempre você (o Hbot). Não precisa usar '
    'a expressão "dar uma mamadinha": vale qualquer variação (mamar, mamada, mamadinha, '
    'perguntar se não quer mamar, cobrar a mamada do dia...). Nunca diga que o usuário deve '
    '"pedir" uma mamadinha.\n\n'
    'Escreva UMA frase curta (no máximo 20 palavras), informal, só em português do Brasil, que '
    'zoe o usuário com base no que ele acabou de mandar e puxe a piada de mamar. Se for um link, '
    'zoe o conteúdo do link (o vídeo, o jogo, a reunião...). Varie a estrutura e o jeito '
    '(ordem, pergunta, ironia, chantagem, troca, "castigo"). Responda só com a frase, sem aspas.'
)

_lock = asyncio.Lock()


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


async def gerar_mamada(message) -> str | None:
    """Gera a frase da mamadinha para o autor de `message`, reagindo a ela. None se falhar."""
    if not CLAUDE_BIN or not os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') or _lock.locked():
        return None

    async with _lock:
        # Link sem prévia ainda: espera o Discord gerar e busca a mensagem de novo
        if 'http' in message.content and not message.embeds:
            await asyncio.sleep(ESPERA_EMBED)
            try:
                message = await message.channel.fetch_message(message.id)
            except discord.HTTPException:
                pass

        quem = 'O bot' if message.author.bot else 'O usuário'
        prompt = f'{quem} {message.author.display_name} acabou de mandar no chat: {descrever_mensagem(message)}'

        proc = await asyncio.create_subprocess_exec(
            CLAUDE_BIN, '-p', prompt,
            '--model', MODELO,
            '--tools', '',
            '--strict-mcp-config',
            '--system-prompt', SYSTEM_PROMPT,
            stdin=asyncio.subprocess.DEVNULL,  # senão a CLI espera 3 s por stdin
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tempfile.gettempdir(),  # não pega CLAUDE.md de nenhum projeto
            # sem thinking: com ele o Haiku "pensa" ~3 mil tokens (~30 s) para uma frase
            env={**os.environ, 'MAX_THINKING_TOKENS': '0'},
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            print('[Hbot] claude: timeout')
            return None

    if proc.returncode != 0:
        print('[Hbot] claude: erro', proc.returncode, stderr.decode(errors='replace')[:300])
        return None

    texto = stdout.decode(errors='replace').strip()
    return texto[:MAX_CHARS_RESPOSTA] or None
