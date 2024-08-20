import os
import discord
from discord.commands import option
from dotenv import dotenv_values
from pymongo import MongoClient

intents = discord.Intents.default()
bot = discord.Bot()

STATUS_NAME_LIST = []
CATEGORY_OPTIONS = ['c', 's']

async def status_name_searcher(ctx: discord.AutocompleteContext):
  return [
    status_name for status_name in STATUS_NAME_LIST if status_name.startswith(ctx.value)
  ]

async def get_categories(ctx: discord.AutocompleteContext):
  return [
    category for category in CATEGORY_OPTIONS if category.startswith(ctx.value.lower())
  ]

@bot.event
async def on_ready():
  print('JJ-8 Activated!!')

@bot.slash_command(name='test', description='テストコマンドです。')
async def test_command(interaction: discord.Interaction):
  await interaction.response.send_message('てすと！', ephemeral=True)

@bot.slash_command(name='sts', description='バフ・デバフを日本語で入力・選択可能。')
@option(
  'status_name',
  description='バフ・デバフを入力/選択ください。',
  autocomplete=status_name_searcher,
)
@option('category',
  description='c:キャラクター,s:シップ (デフォルトはc)',
  autocomplete=get_categories,
  required=False,
)
async def find_status(ctx: discord.ApplicationContext, status_name: str, category: str):
  await ctx.defer()
  result: str = ''

  embeds = []
  my_embed: discord.Embed = None

  try:
    if category is None or category == '':
      cursor = collection.find(filter={'statusName': status_name, 'category': 'c'})
    else:
      cursor = collection.find(filter={'statusName': status_name, 'category': category})

    i: int = 0
    page: int = 1
    before_name = ''
    data_count = 0
    for doc in cursor:
      if my_embed is None:
        my_embed = discord.Embed(
          title=f'__{doc["statusName"]}__ ({doc["statusType"]}) - page {page} -',
          description='',
          color=0x00ff00)

      if doc['unitName'] == before_name:
        current_name = '---'
      else:
        current_name = f'👉{doc["unitName"]}{os.linesep}---'
      my_embed.add_field(name=current_name,
        value=f'- {doc["skillType"]} ： {doc["skillName"]}',
        inline=False)
      
      before_name = doc['unitName']

      if i % 24 == 0 and i != 0:
        embeds.append(my_embed)
        my_embed = None
        page = page + 1
        
      i = i + 1
    
    if my_embed is not None:
      embeds.append(my_embed)
      data_count = i
    
  except StopIteration:
    pass
  finally:
    for embed in embeds:
      await ctx.send(embed=embed)

    if data_count == 0:
      await ctx.followup.send('該当データなし')
    else:
      await ctx.followup.send(f'{data_count}件のデータがヒット')
  
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