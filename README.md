# Hbot

Bot de Discord pessoal em Python (`discord.py`), com uns comandos utilitários e
brincadeiras internas. Persiste dados em PostgreSQL.

- **Comandos:** de barra (`/`), os slash commands nativos do Discord
- **Stack:** Python 3.12 · [discord.py](https://discordpy.readthedocs.io/) · PostgreSQL (via `psycopg`)
- **Deploy:** container Docker no homelab, CI via GitHub Actions — ver [`DEPLOY.md`](DEPLOY.md)

---

## Comandos

São slash commands: digite `/` no chat e o Discord lista os comandos, com a descrição e os
parâmetros de cada um. Parâmetros sem `[]` são obrigatórios; entre `[]` são opcionais. Mensagens de
erro (lista fechada, data inválida, fora do cargo…) aparecem só para quem chamou (efêmeras).

| Comando | Parâmetros | O que faz |
|---|---|---|
| `/help` | — | Lista todos os comandos com uma breve explicação (num embed, só para quem chamou). |
| `/version` | — | Mostra a versão atual do Hbot (string fixa no código, `HBOT_VERSION`). |
| `/del` | `quantidade` (1–500) | Apaga as últimas mensagens do canal e confirma só para quem chamou. Só aparece para quem tem **Gerenciar Mensagens**; o bot também precisa dessa permissão no canal. |
| `/fbe` | `extensao` `[profundidade=100]` | Varre o histórico do canal (até `profundidade` mensagens, máx. 1000) e posta as URLs dos anexos cujo nome termina em `extensao`. Ex.: `/fbe extensao:pdf`. |
| `/mamadas` | — | Mostra quantas "mamadas" **você** acumulou (contador de brincadeira, ver abaixo). |
| `/rank` | — | Ranking de mamadas do servidor. |
| `/presente` | — | Marca presença na sessão de hoje (segunda/quinta, só entre a abertura e o fechamento: 20h–23h). Só para quem tem o cargo da lista. |
| `/ausente` | `motivo` `[quando]` | Avisa que não vai. Sem `quando`, vale a próxima sessão (hoje, se a lista ainda está aberta). Com antecedência (até 32 dias): `quando` sugere as próximas sessões, ou aceita `seg`, `qui`, `DD/MM[/AAAA]`. Abre uma votação (ver abaixo). |
| `/lista` | — | Quem marcou presença/ausência na sessão de hoje (fora de dia de sessão, na próxima) e quem ainda não marcou (ou faltou, depois do fechamento). |
| `/faltas` | `[mes]` (`MM/AAAA`) | Faltas e ausências do mês (padrão: mês atual). |
| `/presenca_config` | `canal` `cargo` | Define o canal dos avisos e o cargo de quem precisa marcar. Só aparece para quem tem **Gerenciar Servidor**. |

Os comandos são registrados no Discord (`tree.sync()`) toda vez que o bot liga. O bot precisa ter sido
convidado com o escopo `applications.commands` (além de `bot`); se os comandos não aparecerem, reconvide
pelo OAuth2 URL Generator do Developer Portal marcando os dois escopos.

---

## Comportamentos automáticos (sem comando)

O bot também reage a mensagens comuns:

### 😈 "Mamadinha" aleatória
A cada mensagem, há **10% de chance** do bot responder mandando a pessoa mamar
(com TTS) e incrementar o contador dela — é o que alimenta `/mamadas` e `/rank`.

A frase é gerada na hora pelo **Claude Code** (CLI `claude -p`, modelo Haiku), reagindo
ao que a pessoa mandou (texto, imagens/arquivos pelo tipo e nome, figurinhas, embeds de
outros bots, e o título da prévia de links — YouTube, Steam etc.; o bot espera 3 s pela prévia) — ver [`BO/mamada.py`](BO/mamada.py), onde ficam o prompt e o sorteio. A chamada ao Claude
em si (CLI, timeout, fila, personalidade comum do Hbot) é genérica, em [`BO/claude.py`](BO/claude.py).
Leva ~3–5 s (o bot mostra "digitando…"). Sem token, com erro ou após 15 s, cai na
frase fixa `Da uma mamadinha aqui <nome>`. Só uma geração por vez; se já tiver uma
rodando, usa a frase fixa.

### 📋 Lista de presença (segunda e quinta)
Lógica e horários em [`BO/presenca.py`](BO/presenca.py) (constantes `ABERTURA`, `LEMBRETE`,
`FECHAMENTO`, `PREMIACAO`, fuso `America/Sao_Paulo`). Precisa de `/presenca_config` uma vez.

- **20h** — o bot abre a lista no canal, mencionando o cargo.
- **21h** — lembrete mencionando só quem do cargo ainda não marcou nada.
- **23h** — fecha: quem não marcou `/presente` nem `/ausente` leva **falta**; o bot posta o resumo.
- **Dia 1, 00:05** — quem teve mais faltas no mês anterior ganha **uma mamada** (empate: todos).
  Ausências avisadas não contam.

As mensagens automáticas (abertura, lembrete, resumo do fechamento, votação aberta, resultado
da votação e rei das faltas) começam com uma frase de zoeira **pesada** gerada pelo Claude, a partir
do contexto (nomes, motivo, resultado) — prompts em [`BO/presenca_mensagens.py`](BO/presenca_mensagens.py).
A piada da mamada só entra no rei das faltas. Menções, horários, placar e listas ficam no texto fixo
logo abaixo (o Claude nunca é a fonte da informação); sem Claude, sai só o texto fixo. As mensagens só
notificam quem o código menciona (`allowed_mentions`), então um `@everyone` gerado não pinga ninguém.

`/presente` só vale entre a abertura e o fechamento (20h–23h) do dia da sessão; `/ausente` também pode ser marcado
com antecedência para qualquer sessão futura. Um sobrescreve o outro (quem avisou ausência e
resolveu ir, é só dar `/presente` depois que a lista abrir — se a votação ainda estiver aberta, ela é cancelada).

**Votação da ausência.** Cada `/ausente` abre uma **enquete do Discord** no canal da lista
(✅ Aprovo / ❌ Não aprovo). Enquanto isso a ausência fica "em votação" (não leva lembrete nem falta).
- Votam os membros do cargo, **menos quem pediu**; votos de fora do cargo são ignorados na contagem.
- **Quem não vota conta a favor**: é reprovada se **metade ou mais** dos votantes votar ❌ (empate reprova).
- A enquete encerra quando **todos os votantes votarem** ou no **fechamento da sessão** (23h do dia) —
  mesmo que o resultado já esteja decidido antes.
- Aprovada → ausência. Reprovada com a lista aberta → a marcação some (ainda dá pra `/presente`);
  reprovada depois do fechamento → **falta**.
- O bot precisa da permissão **Enviar Enquetes** no canal. Votações vencidas com o bot fora do ar são
  apuradas quando ele volta (loop a cada 5 min).
Se o bot estiver fora do ar no fechamento ou na premiação, ele faz em silêncio quando volta
(só o fechamento do próprio dia).

### Outras reações
- Mensagem contendo a palavra **`prune`** → o bot reclama e sugere usar `/del`.

---

## ⚠️ Comportamentos legados hardcoded

Ficaram no código do bot antigo, com **IDs de usuário fixos**. Documentado aqui pra
ficar visível — provavelmente vale limpar/revisar (`main.py`, `on_message`):

- Um usuário específico (ID `184405311681986560`) recebe `Bot lixo!` como resposta.

---

## Banco de dados

PostgreSQL, tabela `usuarios`. Um registro por
usuário **por servidor**:

| Coluna | Descrição |
|---|---|
| `cd_servidor` | ID do servidor Discord |
| `cd_user` | ID do usuário Discord |
| `nome` | Nome do usuário |
| `qtd_mamadas` | Contador de mamadas |

Lista de presença: `presenca_config` (canal/cargo por servidor), `presencas` (um registro por
usuário/servidor/dia, `status` = `presente` | `ausente` | `pendente` | `falta`, `motivo`, mensagem da enquete) e
`presenca_premiacoes` (meses já premiados).

### Migrations
O schema fica em arquivos `.sql` numerados em [`migrations/`](migrations/), aplicados em ordem quando
o bot liga ([`BO/migrations.py`](BO/migrations.py)). A tabela `schema_migrations` guarda quais já
rodaram; cada uma roda uma vez, numa transação (com erro, nada dela fica no banco e o bot não sobe).

Para mudar o banco, **crie um arquivo novo** (ex.: `migrations/0003_adiciona_coluna_x.sql` com um
`ALTER TABLE`) — nunca edite uma migration que já rodou em produção.

Conexão via variável de ambiente `DATABASE_URL`.

---

## Rodar / fazer deploy

- **Produção (homelab):** container Docker + PostgreSQL compartilhado, deploy contínuo
  via GitHub Actions. Passo a passo completo em [`DEPLOY.md`](DEPLOY.md).
- **Variáveis de ambiente:** `TOKEN` (token do bot), `DATABASE_URL` e, opcional, `CLAUDE_CODE_OAUTH_TOKEN`. Ver [`.env.example`](.env.example).
- **Intents privilegiados:** o bot precisa de **MESSAGE CONTENT** e **SERVER MEMBERS**
  ligados no [Discord Developer Portal](https://discord.com/developers/applications) —
  sem o Message Content, a mamada aleatória e o aviso do `prune` param de funcionar.

### Desenvolvimento local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TOKEN=seu_token
export DATABASE_URL=postgresql://hbot:senha@localhost:5432/hbot
python main.py
```
