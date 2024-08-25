import os
import discord

from discord.commands import option
from dotenv import dotenv_values
import requests
from pymongo import MongoClient

intents = discord.Intents.default()
bot = discord.Bot()

async def status_name_searcher(ctx: discord.AutocompleteContext):
  STATUS_NAME_LIST = list(db['status'].distinct('statusName'))
  return [
    status_name for status_name in STATUS_NAME_LIST if status_name.startswith(ctx.value)
  ]

async def get_categories(ctx: discord.AutocompleteContext):
  return [
    category for category in ['c', 's'] if category.startswith(ctx.value.lower())
  ]

async def get_phase_list(ctx: discord.AutocompleteContext):
  return [
    phase for phase in ['1', '2', '3', '4', '5', '6'] if phase == ctx.value
  ]

async def get_player_info(ally_code):
  loc = f'https://swgoh.gg/api/player/{ally_code}/'
  header = {"content-type": "application/json"}
  r = requests.get(loc, headers=header)
  all_data = r.json()
  player_info = all_data['data']
  
  return player_info

async def get_guild_info(guild_id):
  loc = f'https://swgoh.gg/api/guild-profile/{guild_id}/'
  header = {"content-type": "application/json"}
  r = requests.get(loc, headers=header)
  guild_info = r.json()
  return guild_info['data']

@bot.event
async def on_ready():
  print('JJ-8 Activated!!')

#######################################
## RoteTB シミュレータ
######################################
@bot.slash_command(name='gtb', description='RotE TBの指定フェーズをシミュレートします。')
@option(
  'phase',
  description='フェーズを入力・選択。',
  autocomplete=get_phase_list,
)
async def simulate_tb(ctx: discord.ApplicationContext, phase: int):
  await ctx.defer()
  cursor = db['player'].find(filter={'userName': ctx.author.name})
  
  ally_code: str = ''
  for doc in cursor:
    ally_code = doc['allyCode']
  
  if ally_code == '':
    await ctx.followup.send('```ERROR: 同盟コードの事前登録が必要です。```')
    return
  
  player_info = await get_player_info(ally_code)

  guild_info = await get_guild_info(player_info['guild_id'])
  guild_name = guild_info['name']
  guild_gp = guild_info['galactic_power']
  
  line: str = f'【フェーズ {phase}】 ポイント詳細{os.linesep}----------{os.linesep}'
  totalPoints = 0
  cursor = db['tbRote'].find(filter={'phase': phase})
  for doc in cursor:
    line = line + f'[{doc["sideAbbr"]}]:{doc["planetJp"]}{os.linesep}'
    line = line + f'★1:{doc["star1"]:>11,}|★2:{doc["star2"]:>11,}|★3:{doc["star3"]:>11,}{os.linesep}'
    totalPoints = totalPoints + doc["star3"]
  
  line = line + f'----------{os.linesep}合計: {totalPoints:>11,}'
  await ctx.send(f'```{line}```')

  my_embed = discord.Embed(
    title=f'RoteTB【フェーズ {phase}】',
    description=f'ギルド名: {guild_name} | 総GP: {guild_gp}',
    color=0x00ff00)
  
  shortage = guild_gp - totalPoints
  if (shortage < 0):
    my_embed.add_field(name=f'ギルドGPが不足しています。',
      value=f'不足分: {shortage:>11,}', inline=False)
  else:
    my_embed.add_field(name=f'ギルドGPのみで全エリアの★3取得可能です。',
      value=f'超過分: {shortage:>11,}', inline=False)
  
  await ctx.followup.send(embed=my_embed)

#######################################
## 同盟コード登録
######################################
@bot.slash_command(name='register', description='自身の同盟コードを登録します。')
@option(
  'ally_code',
  description='同盟コードを入力ください。',
)
async def register_ally_code(ctx: discord.ApplicationContext, ally_code: str):
  await ctx.defer()

  # update({"name": "hoge"}, {"$set": {"age": 25}})
  count: int = db['player'].count_documents(
    filter={'allyCode': ally_code}
  )
  if count > 0:
    await ctx.followup.send('```ERROR: 登録済の同盟コードです！```')
    return

  player_info = await get_player_info(ally_code)
  guild_id = player_info['guild_id']
  guild_name = player_info['guild_name']

  db['player'].insert_one(
    {
      'displayName': ctx.author.display_name,
      'userName': ctx.author.name,
      'allyCode': ally_code,
      'guildId': guild_id,
      'guildName': guild_name
    }
  )

  await ctx.followup.send(f'SUCCESS: 同盟コード({ally_code})の登録が完了しました！')
 
#######################################
## 同盟コード登録解除
#######################################
@bot.slash_command(name='unregister', description='同盟コードの登録を解除します。')
@option(
  'ally_code',
  description='同盟コードを入力ください。',
)
async def unregister_ally_code(ctx: discord.ApplicationContext, ally_code: str):
  await ctx.defer()

  count: int = db['player'].count_documents(
    filter={'allyCode': ally_code}
  )
  if count == 0:
    await ctx.followup.send('```ERROR: 存在しない同盟コードです！```')
    return

  db['player'].delete_one({'allyCode': ally_code})
  await ctx.followup.send(f'SUCCESS: 同盟コード({ally_code})の登録が解除されました！')

#######################################
## ギルドメンバー同盟コード取得
#######################################
@bot.slash_command(name='allys', description='全ギルドメンバーの同盟コードを取得します。同盟コードの事前登録が必要です。')
async def get_members_ally_code(ctx: discord.ApplicationContext):
  await ctx.defer()

  cursor = db['player'].find(filter={'userName': ctx.author.name})
  
  ally_code: str = ''
  for doc in cursor:
    ally_code = doc['allyCode']
  
  if ally_code == '':
    await ctx.followup.send('```ERROR: 同盟コードの事前登録が必要です。```')
    return
  
  player_info = await get_player_info(ally_code)
  guild_id = player_info["guild_id"]

  # loc = f'https://swgoh.gg/api/guild-profile/{guild_id}/'
  # r = requests.get(loc, headers=header)
  # all_data = r.json()
  guild_info = await get_guild_info(guild_id)
  members = guild_info['members']

  my_embed = discord.Embed(
    title=f'ギルド名: {player_info["guild_name"]}{os.linesep}ギルドID: {guild_id}',
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
      cursor = db['status'].find(
        filter={'statusName': status_name, 'category': 'c'})
    else:
      cursor = db['status'].find(
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
      title = '__該当データなし__'
      description = f'categoryオプションをお試しください。{os.linesep} - c: キャラクター{os.linesep}- s: シップ'
    else:
      await ctx.send(line)
      title = f'{title}'
      description = f'{i}件のデータがヒット'

    my_embed = discord.Embed(title=f'{title}', description=description, color=0x00ff00)

    await ctx.followup.send(embed=my_embed)
  
##################
# グローバル処理
##################
dirname = os.path.dirname(__file__)
path = os.path.join(dirname, '.env')
config = dotenv_values(dotenv_path=path)

# DB, collection設定
db_client = MongoClient(config['MONGODB_URI'])
db = db_client['swgoh']

# Bot実行
bot.run(config['TOKEN'])