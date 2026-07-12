# Hbot

Bot de Discord pessoal em Python (`discord.py`), com uns comandos utilitários, um
mini-RPG de contadores e brincadeiras internas. Persiste dados em PostgreSQL.

- **Prefixo dos comandos:** `h.`
- **Stack:** Python 3.12 · [discord.py](https://discordpy.readthedocs.io/) · PostgreSQL (via `psycopg`)
- **Deploy:** container Docker no homelab, CI via GitHub Actions — ver [`DEPLOY.md`](DEPLOY.md)

---

## Comandos

Todos usam o prefixo `h.`. Argumentos entre `<>` são obrigatórios; entre `[]` são opcionais.

| Comando | Argumentos | O que faz |
|---|---|---|
| `h.help` | — | Lista todos os comandos com uma breve explicação (num embed). |
| `h.del` | `<n>` | Apaga as últimas `n` mensagens do canal (mais o próprio comando) e responde 👍. `n` precisa ser positivo. Requer permissão **Gerenciar Mensagens**. |
| `h.fbe` | `<ext> [profundidade=100]` | Varre o histórico do canal (até `profundidade` mensagens) e posta as URLs dos anexos cujo nome termina em `<ext>`. Ex.: `h.fbe pdf 50`. |
| `h.mamadas` | — | Mostra quantas "mamadas" **você** acumulou (contador de brincadeira, ver abaixo). |
| `h.rank` | — | Ranking de mamadas do servidor. |
| `h.gold` | `[qtd]` | Sem argumento: mostra seu **gold**. Com argumento: **soma** `qtd` ao seu gold (aceita negativo). |
| `h.set_gold` | `<qtd>` | Define seu gold para `qtd` (valor absoluto). |
| `h.pp` | `[qtd]` | Sem argumento: mostra seus **PPs**. Com argumento: **soma** `qtd`. |
| `h.set_pp` | `<qtd>` | Define seus PPs para `qtd`. |

> `gold` e `pp` são dois contadores independentes por usuário/servidor — um mini-RPG
> sem regra fixa, só pra marcar pontos manualmente.

---

## Comportamentos automáticos (sem comando)

O bot também reage a mensagens comuns:

### 🎲 Rolagem de dados
Se uma mensagem contém um padrão de dado, o bot rola e responde com o total e os
valores individuais.

- Formato: `<qtd>d<lados>` (a quantidade é opcional). Ex.: `d20`, `2d6`, `10d4`.
- Dá pra combinar **dois grupos de dados** com um operador `+ - * /`. Ex.: `1d20+1d6`, `2d8*1d4`.
- ⚠️ Modificador numérico fixo **não** é suportado: em `1d20+5`, o `+5` é ignorado
  (o segundo operando precisa ser outro dado, tipo `1d20+1d6`).

Exemplo de resposta para `2d6`:
```
9 <- [4, 5] 2d6
```

### 😈 "Mamadinha" aleatória
A cada mensagem, há **10% de chance** do bot responder mandando a pessoa mamar
(com TTS) e incrementar o contador dela — é o que alimenta `h.mamadas` e `h.rank`.

### Outras reações
- Mensagem contendo a palavra **`prune`** → o bot reclama e sugere usar `h.del`.

---

## ⚠️ Comportamentos legados hardcoded

Ficaram no código do bot antigo, com **IDs de usuário fixos**. Documentado aqui pra
ficar visível — provavelmente vale limpar/revisar (`main.py`, `on_message`):

- Um usuário específico (ID `184405311681986560`) recebe `Bot lixo!` como resposta.

---

## Banco de dados

PostgreSQL, tabela `usuarios` (criada automaticamente no boot). Um registro por
usuário **por servidor**:

| Coluna | Descrição |
|---|---|
| `cd_servidor` | ID do servidor Discord |
| `cd_user` | ID do usuário Discord |
| `nome` | Nome do usuário |
| `qtd_mamadas` | Contador de mamadas |
| `gold`, `pp` | Contadores do mini-RPG |

Conexão via variável de ambiente `DATABASE_URL`.

---

## Rodar / fazer deploy

- **Produção (homelab):** container Docker + PostgreSQL compartilhado, deploy contínuo
  via GitHub Actions. Passo a passo completo em [`DEPLOY.md`](DEPLOY.md).
- **Variáveis de ambiente:** `TOKEN` (token do bot) e `DATABASE_URL`. Ver [`.env.example`](.env.example).
- **Intents privilegiados:** o bot precisa de **MESSAGE CONTENT** e **SERVER MEMBERS**
  ligados no [Discord Developer Portal](https://discord.com/developers/applications) —
  sem o Message Content, ele fica online mas os comandos não respondem.

### Desenvolvimento local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TOKEN=seu_token
export DATABASE_URL=postgresql://hbot:senha@localhost:5432/hbot
python main.py
```
