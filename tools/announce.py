"""Envia uma mensagem única para TODOS os servidores em que o bot está.

Utilitário de uso pontual (não faz parte do bot em si). A mensagem vem por argumento,
então não precisa editar este arquivo. Por padrão roda em dry-run (só lista os alvos,
não envia nada); só envia de verdade com --send.

Precisa da env var TOKEN.

Uso local:
    python tools/announce.py "sua mensagem aqui"        # dry-run (não envia)
    python tools/announce.py --send "sua mensagem aqui" # envia de verdade

No homelab (container descartável com a imagem do bot), a partir de /home/hman/discord-bot/app:
    docker run --rm --env-file .env -v "$PWD/tools/announce.py:/announce.py" app-bot \
        python -u /announce.py --send "Voltei!"
"""
import os
import sys

import discord


def _load_dotenv(path=".env"):
    """Carrega variáveis de um .env para o os.environ, sem depender de libs externas.
    Não sobrescreve o que já estiver definido no ambiente."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                chave, _, valor = line.partition("=")
                os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv()

args = sys.argv[1:]
send = "--send" in args
mensagem = " ".join(a for a in args if a != "--send").strip()

if not mensagem:
    sys.exit('Uso: python announce.py [--send] "sua mensagem"')

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Conectado como {client.user} | servidores: {len(client.guilds)}")
    print(f"Mensagem: {mensagem!r}")
    print(f"Modo: {'ENVIO REAL' if send else 'DRY-RUN (nada enviado)'}")
    print("-" * 50)
    for guild in client.guilds:
        canal = None
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            canal = guild.system_channel
        else:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    canal = ch
                    break
        if canal is None:
            print(f"[SKIP] {guild.name}: nenhum canal com permissão de envio")
            continue
        print(f"{guild.name}  ->  #{canal.name}")
        if send:
            try:
                await canal.send(mensagem)
                print("   enviado ✓")
            except Exception as e:  # noqa: BLE001
                print(f"   [ERRO] {e}")
    await client.close()


token = os.environ.get("TOKEN")
if not token:
    sys.exit("Erro: TOKEN não definido. Preencha o .env (TOKEN=...) ou exporte a variável.")

client.run(token)
