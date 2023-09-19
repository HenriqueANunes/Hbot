from discord.ext import commands
from keep_alive import keep_alive

import discord
import os
import asyncio
import random
import BO.usuario
import BO.rpg
# import aiocron

# logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)

client = commands.Bot(command_prefix="h.", intents=intents)

blackList = ['jpeg', 'jpg', 'png', 'gif']


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    # Envia mensagem privada

    """"
	gex = client.get_user(205352729315377153)
	await gex.send("gex gay\nMe diz se funcionou kkk")
	lima = client.get_user(209430765044236288)
	await lima.send("o queeeee\nMe diz se funcionou kkk")
	matheus = client.get_user(553192451758882817)
	await matheus.send("o queeeee\nMe diz se funcionou kkk")

	antonio = client.get_user(306172735732580353)
	await antonio.send("O queeee")
	await antonio.send("Mama antoniooo!")
	await antonio.send("kkkkkk")
	await antonio.send("PS: me diz se funcionou kkk")
	"""

    # A cada 5s marca o gex e manda um gex gay em todos os canais
    """
	while True:
		canais = guilda.text_channels
		# print(canais)
		for canal in canais:
			# print(canal.name)
			await canal.send("<@205352729315377153> gex gay")

		await asyncio.sleep(180)
	"""


@client.listen()
async def on_message(message):
    if message.author == client.user:
        return

    if message.author == client.get_user(502671975978631183):
        mensagem = f'{str(message.author)}: {message.content}'
        hman = client.get_user(279274104043995136)
        await hman.send(mensagem)

    if 'prune' in message.content.lower():
        await message.channel.send('Não pode usar esse comando lixo!!')
        await message.channel.send('Use h.del')

    if message.author == client.get_user('184405311681986560'):
        await message.channel.send('Bot lixo!')

    # Manda o Maestrelli mamar em todas as mensagens q ele mandar
    """
    if message.author == client.get_user(249942644501774338):
        await message.channel.send("Mama boiostrelli!")
    """

    # Quando um usuario envia uma mensagem no chat, há uma chance de o bot mandar ele mamar
    rng = random.random()
    if rng <= 0.1:
        await message.channel.send(
            f'Da uma mamadinha aqui {message.author.display_name}', tts=True)
        BO.usuario.Usuario(user=message.author, cd_servidor=message.guild.id).add_mamada()


    response = BO.rpg.Rpg().get_dados(regex=message.content.lower())

    if response:
        await message.channel.send(response)

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
                                           cd_servidor=ctx.guild.id).set_gold(qtd_pp=qtd_pp)

    await ctx.channel.send(descricao)

# @aiocron.crontab('*/10 * * * *')
# async def cronjob1():

#     canal = client.get_channel(928011484980732026)
#     await canal.send('Testando cron do Hbot')

# @aiocron.crontab('0 17 * * *')
# async def conjob2():
#     maria = client.get_user(502671975978631183)
#     await maria.send("Grêmio volta a perder para o Palmeiras e está eliminado do Brasileirão Feminino.")

#     hman = client.get_user(279274104043995136)
#     await hman.send("Grêmio volta a perder para o Palmeiras e está eliminado do Brasileirão Feminino.")


keep_alive()
try:
    client.run(os.getenv('TOKEN'))
except:
    os.system('kill 1')
    client.run(os.getenv('TOKEN'))
