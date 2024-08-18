import os
import discord
from discord.commands import option
from dotenv import dotenv_values
from pymongo import MongoClient

intents = discord.Intents.default()
bot = discord.Bot()

STATUS_NAME_LIST = []

async def status_name_searcher(ctx: discord.AutocompleteContext):
    #print(ctx.value)
    return [
        status_name for status_name in STATUS_NAME_LIST if status_name.startswith(ctx.value)
    ]

@bot.event
async def on_ready():
  print("jstat Bot起動完了！")

@bot.slash_command(name="test", description="テストコマンドです。")
async def test_command(interaction: discord.Interaction):
  await interaction.response.send_message("てすと！", ephemeral=True)

@bot.slash_command(name="sts")
@option(
    "status_name",
    description="バフ・デバフを日本語で入力/選択できます",
    autocomplete=status_name_searcher,
)
async def find_status(ctx: discord.ApplicationContext, status_name: str):
  await ctx.defer()
  result: str = ""

  embeds = []
  my_embed: discord.Embed = None

  try:
    cursor = collection.find(filter={'statusName': status_name, 'category': 'c'})

    i: int = 0
    page: int = 1
    for doc in cursor:
      if my_embed is None:
        my_embed = discord.Embed(
          title=f'{doc["statusName"]} -{doc["statusType"]}- (page {page})',
          description='',
          color=0x00ff00)

      my_embed.add_field(name=doc["unitName"],
        value=f'{doc["skillType"]} ： {doc["skillName"]}',
        inline=False)
      if i % 24 == 0 and i != 0:
        embeds.append(my_embed)
        my_embed = None
        page = page + 1
        
      i = i + 1
    
    if my_embed is not None:
      embeds.append(my_embed)
    
  except StopIteration:
    pass
  finally:
    for embed in embeds:
      await ctx.send(embed=embed)
    #await ctx.send(embed=my_embed)
    await ctx.followup.send("---")

  #embed.add_field(name='Unit Info', value=result, inline=False)
  
##################
# グローバル処理
##################
dirname = os.path.dirname(__file__)
path = os.path.join(dirname, '.env')
config = dotenv_values(dotenv_path=path)

# DB, collection設定
uri = config['MONGODB_URI']
db_client = MongoClient(uri)
db = db_client['swgoh']
collection = db[config['COLLECTION_NAME']]

# autocomplete用のリストを作成
STATUS_NAME_LIST = list(collection.distinct('statusName'))

# Bot実行
bot.run(config['TOKEN'])