import asyncio
import os
import shutil
import tempfile

"""
Geração de texto com o Claude Code (CLI `claude`) em modo não interativo.

- Autenticação via variável de ambiente `CLAUDE_CODE_OAUTH_TOKEN`
  (gerada uma vez com `claude setup-token`; usa a assinatura, não créditos de API).
- Sem o binário ou sem o token, `gerar` devolve None e quem chamou usa um texto fixo.
- Só uma chamada por vez (protege a CPU do servidor e o limite da assinatura). Com
  `esperar=False`, se já tiver uma rodando, devolve None na hora; com `esperar=True`,
  aguarda a vez.

Cada uso (mamada, presença...) monta o próprio prompt e as próprias instruções;
a personalidade do Hbot (PERSONA) vem na frente das instruções de todos.
"""

CLAUDE_BIN = shutil.which('claude')
MODELO = 'haiku'
TIMEOUT = 15  # segundos (sem thinking leva ~2–5 s)
MAX_CHARS_RESPOSTA = 300

# Personalidade comum a todas as gerações — personalizar aqui.
PERSONA = 'Você é o Hbot, bot zoeiro de um servidor de Discord entre amigos.'

_lock = asyncio.Lock()


def disponivel() -> bool:
    return bool(CLAUDE_BIN and os.environ.get('CLAUDE_CODE_OAUTH_TOKEN'))


async def gerar(prompt: str, instrucoes: str, *, esperar: bool = False) -> str | None:
    """Gera um texto para `prompt` seguindo PERSONA + `instrucoes`. None se falhar."""
    if not disponivel() or (_lock.locked() and not esperar):
        return None

    async with _lock:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_BIN, '-p', prompt,
            '--model', MODELO,
            '--tools', '',
            '--strict-mcp-config',
            '--system-prompt', f'{PERSONA} {instrucoes}',
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
