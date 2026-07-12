from discord.ext import commands

import discord
import os
import asyncio
import random
import BO.usuario
import BO.rpg
# import aiocron

# logging.basicConfig(level=logging.INFO)

# Versão do Hbot — aumente a cada alteração no código
HBOT_VERSION = "1.0.1"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # privilegiado: necessário p/ ler message.content e comandos por prefixo

client = discord.Client(intents=intents)

client = commands.Bot(command_prefix="h.", intents=intents, help_command=None)

blackList = ['jpeg', 'jpg', 'png', 'gif']


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')


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
    rng = random.random()
    if rng <= 0.1:
        await message.channel.send(
            f'Da uma mamadinha aqui {message.author.display_name}', tts=True)
        BO.usuario.Usuario(user=message.author, cd_servidor=message.guild.id).add_mamada()


    response = BO.rpg.Rpg().get_dados(regex=message.content.lower())

    if response:
        await message.channel.send(response)

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
    embed.add_field(name="h.gold [qtd]",
                    value="Sem valor: mostra seu gold. Com valor: soma ao seu gold.", inline=False)
    embed.add_field(name="h.set_gold <qtd>", value="Define seu gold para o valor informado.", inline=False)
    embed.add_field(name="h.pp [qtd]",
                    value="Sem valor: mostra seus PPs. Com valor: soma aos seus PPs.", inline=False)
    embed.add_field(name="h.set_pp <qtd>", value="Define seus PPs para o valor informado.", inline=False)
    embed.add_field(name="🎲 Rolagem de dados",
                    value="Não é comando: escreva algo como `2d6` ou `1d20+1d6` que eu rolo os dados.", inline=False)
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

@client.command(name="gold")
async def get_gold(ctx, qtd_gold:int=None):
    if qtd_gold:
        status, descricao, gold = BO.usuario.Usuario(user=ctx.author,
                                                     cd_servidor=ctx.guild.id).add_gold(qtd_gold=qtd_gold)
    else:
        status, descricao, gold = BO.usuario.Usuario(user=ctx.author,
                                             cd_servidor=ctx.guild.id).get_gold()
        
    if status:
        await ctx.channel.send(str(gold) + ' Gold')
    else: 
        await ctx.channel.send(descricao)

@client.command(name="set_gold")
async def set_gold(ctx, qtd_gold:int=None):
    status, descricao = BO.usuario.Usuario(user=ctx.author,
                                           cd_servidor=ctx.guild.id).set_gold(qtd_gold=qtd_gold)

    await ctx.channel.send(descricao)


@client.command(name="pp")
async def get_pp(ctx, qtd_pp:int=None):
    if qtd_pp:
        status, descricao, pp = BO.usuario.Usuario(user=ctx.author,
                                                     cd_servidor=ctx.guild.id).add_pp(qtd_pp=qtd_pp)
    else:
        status, descricao, pp = BO.usuario.Usuario(user=ctx.author,
                                             cd_servidor=ctx.guild.id).get_pp()
        
    if status:
        await ctx.channel.send(str(pp) + ' PPs')
    else:
        await ctx.channel.send(descricao)

@client.command(name="set_pp")
async def set_pp(ctx, qtd_pp:int=None):
    status, descricao = BO.usuario.Usuario(user=ctx.author,
                                           cd_servidor=ctx.guild.id).set_pp(qtd_pp=qtd_pp)

    await ctx.channel.send(descricao)

BO.usuario.init_db()
client.run(os.getenv('TOKEN'))
