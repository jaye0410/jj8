import os
import discord

from discord.commands import option
from dotenv import dotenv_values
import requests
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

## 同盟コード登録
@bot.slash_command(name='register', description='自身の同盟コードを登録します。')
@option(
  'ally_code',
  description='同盟コードを入力ください。',
)
async def register_ally_code(ctx: discord.ApplicationContext, ally_code: str):
  await ctx.defer()

  # update({"name": "hoge"}, {"$set": {"age": 25}})
  count: int = collection_player.count_documents(
    filter={'allyCode': ally_code}
  )
  if count > 0:
    await ctx.followup.send('```ERROR: 登録済の同盟コードです！```')
    return

  loc = f'https://swgoh.gg/api/player/{ally_code}/'
  header = {"content-type": "application/json"}
  r = requests.get(loc, headers=header)
  all_data = r.json()
  player_data = all_data['data']
  guild_id = player_data['guild_id']
  guild_name = player_data['guild_name']

  collection_player.insert_one(
    {
      'displayName': ctx.author.display_name,
      'userName': ctx.author.name,
      'allyCode': ally_code,
      'guildId': guild_id,
      'guildName': guild_name
    }
  )

  await ctx.followup.send(f'SUCCESS: 同盟コード({ally_code})の登録が完了しました！')

## 同盟コード登録解除
@bot.slash_command(name='unregister', description='同盟コードの登録を解除します。')
@option(
  'ally_code',
  description='同盟コードを入力ください。',
)
async def unregister_ally_code(ctx: discord.ApplicationContext, ally_code: str):
  await ctx.defer()

  count: int = collection_player.count_documents(
    filter={'allyCode': ally_code}
  )
  if count == 0:
    await ctx.followup.send('```ERROR: 存在しない同盟コードです！```')
    return

  collection_player.delete_one({'allyCode': ally_code})
  await ctx.followup.send(f'SUCCESS: 同盟コード({ally_code})の登録が解除されました！')

## ギルドメンバー同盟コード取得
@bot.slash_command(name='allys', description='全ギルドメンバーの同盟コードを取得します。同盟コードの事前登録が必要です。')
async def get_members_ally_code(ctx: discord.ApplicationContext):
  await ctx.defer()

  cursor = collection_player.find(filter={'userName': ctx.author.name})
  
  ally_code: str = ''
  for doc in cursor:
    ally_code = doc['allyCode']
  
  if ally_code == '':
    await ctx.followup.send('```ERROR: 同盟コードの事前登録が必要です。```')
    return
  
  loc = f'https://swgoh.gg/api/player/{ally_code}/'
  header = {"content-type": "application/json"}
  r = requests.get(loc, headers=header)
  all_data = r.json()
  player_data = all_data['data']
  guild_id = player_data["guild_id"]

  loc = f'https://swgoh.gg/api/guild-profile/{guild_id}/'
  r = requests.get(loc, headers=header)
  all_data = r.json()
  members = all_data['data']['members']

  my_embed = discord.Embed(
    title=f'ギルド名: {player_data["guild_name"]}{os.linesep}ギルドID: {guild_id}',
    description='',
    color=0x00ff00)
  
  line: str = ''
  for member in members:
    line = line + f'{os.linesep}{member["player_name"]}: {member["ally_code"]}'

  await ctx.send(f'```{line}```')

  await ctx.followup.send(embed=my_embed)

#######################################
## バフ・デバフ検索
#######################################
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

  try:
    if category is None or category == '':
      cursor = collection_status.find(
        filter={'statusName': status_name, 'category': 'c'})
    else:
      cursor = collection_status.find(
        filter={'statusName': status_name, 'category': category})

    my_embed: discord.Embed = None
    i: int = 0
    title: str = ''
    line: str = ''
    
    for doc in cursor:
      if my_embed is None:
        title = f'__{doc["statusName"]}__ ({doc["statusType"]})'

      line = line + f'```{doc["unitName"]} ({doc["skillType"]}) {doc["skillName"]}```'
        
      i = i + 1
    
  except StopIteration:
    await ctx.followup.send('ERROR: Unexpected exception occured.')
    pass
  finally:
    if i == 0:
      my_embed = discord.Embed(
        title=f'__該当データなし__',
        description=f'categoryオプションをお試しください。{os.linesep} - c: キャラクター{os.linesep}- s: シップ',
        color=0x00ff00)
    else:
      await ctx.send(line)
      my_embed = discord.Embed(
        title=f'{title}',
        description=f'{i}件のデータがヒット',
        color=0x00ff00)

    await ctx.followup.send(embed=my_embed)
  
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
collection_status = db['status']
collection_player = db['player']

# autocomplete用のリストを作成
STATUS_NAME_LIST = list(collection_status.distinct('statusName'))

# Bot実行
bot.run(config['TOKEN'])