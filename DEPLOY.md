# Deploy do Hbot no homelab

Bot de Discord (Python + discord.py) com persistência em **PostgreSQL compartilhado**,
rodando como stack Docker no servidor ([[Portainer]]). Convenções do homelab: bind
mount em `/home/hman/<app>/`, restart `unless-stopped`, segredos via `.env`
(guardados no Vaultwarden, nunca commitados).

## Arquitetura
```
[stack postgres]  postgres:16  ──rede docker `postgres`──  [stack hbot]  bot (python)
   dbs: hbot, my_platform, ...                                 DATABASE_URL → postgres:5432/hbot
```
- O Postgres é **um só container, compartilhado** entre projetos (hbot, futuramente `my_platform`),
  cada um com **seu próprio banco e usuário**. Ver nota `[[PostgreSQL]]` no vault do homelab.
- A stack do hbot **não** sobe banco: só o container `bot`, que conecta no Postgres
  compartilhado pela rede Docker externa `postgres`.
- O bot cria a tabela `usuarios` sozinho no primeiro boot (com retry enquanto o banco não responde).

---

## Pré-requisito: Postgres compartilhado (fazer uma vez)

Se a stack `postgres` ainda não existe no servidor, suba-a primeiro. Compose sugerido
(pasta `/home/hman/postgres/`), também documentado em `[[PostgreSQL]]` no vault:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_SUPERUSER_PASSWORD:?}
    volumes:
      - /home/hman/postgres/data:/var/lib/postgresql/data
    networks:
      - postgres
networks:
  postgres:
    name: postgres
```

A senha do superusuário `postgres` vai no `.env` dessa stack e no Vaultwarden.

### Provisionar o banco/usuário do hbot (uma vez)
Com a stack `postgres` no ar:
```bash
docker exec -it postgres psql -U postgres -c \
  "CREATE USER hbot WITH PASSWORD 'GERE_UMA_SENHA_FORTE';"
docker exec -it postgres psql -U postgres -c \
  "CREATE DATABASE hbot OWNER hbot;"
```
Guarde a senha do `hbot` no Vaultwarden — é ela que vai no `DATABASE_URL` do bot.
(Para o `my_platform` no futuro: repetir criando `my_platform` user + database.)

---

## Variáveis de ambiente do bot (`.env`)
Copie `.env.example` para `.env` e preencha:

| Var | O quê |
|-----|-------|
| `TOKEN` | Token do bot (Discord Developer Portal → Bot). Guardar no Vaultwarden. |
| `DATABASE_URL` | `postgresql://hbot:<senha>@postgres:5432/hbot` — host `postgres` é o nome do serviço na rede compartilhada. |

## Antes de subir — no Discord Developer Portal
O bot lê o conteúdo das mensagens (comandos por prefixo `h.`), então habilite os
**Privileged Gateway Intents**:
- ✅ **MESSAGE CONTENT INTENT**
- ✅ **SERVER MEMBERS INTENT**

(No código já estão ligados: `intents.message_content` e `intents.members`.)

## Subir o bot (via SSH — build no servidor)
```bash
ssh hserver
mkdir -p /home/hman/discord-bot
cd /home/hman/discord-bot
git clone <URL_DO_REPO_GITHUB> app   # ou git pull se já existir
cd app
cp .env.example .env
nano .env                            # preencher TOKEN e DATABASE_URL
docker compose up -d --build
docker compose logs -f bot           # deve mostrar "[Hbot] Banco pronto." e "Logged in as ..."
```
> A rede `postgres` precisa existir (criada pela stack `postgres`). Se der
> `network postgres declared as external, but could not be found`, suba a stack `postgres` antes.

## Atualizar o bot depois
```bash
cd /home/hman/discord-bot/app
git pull
docker compose up -d --build
```

## Backup do banco
Como o Postgres é compartilhado, o backup deve cobrir todos os bancos de uma vez
(ex.: `pg_dumpall` ou `pg_dump` por base) — a definir, junto da linha de backup do homelab.
Dados em `/home/hman/postgres/data`.
