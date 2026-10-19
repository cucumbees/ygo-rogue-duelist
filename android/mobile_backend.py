"""Thin mobile transport over the shared campaign rules."""
import json, random, re, time
import campaign as g, content, storage, achievement_model, passives

run=None

def partial(result=None, persist=False, **patch):
 return json.dumps(dict(partial=True,persist=persist,result=result,**patch),ensure_ascii=False)

def state():
 storage.registered_cards()
 storage.register_collection(run)
 return dict(registeredCards=storage.registered_cards(),history=storage.run_history(),run=run,slots=storage.run_slots(),activeSlot=storage.active_slot(),profile=storage.profile(),settings=storage.settings(),achievements=achievement_model.entries())

def dispatch(raw):
 global run
 req=json.loads(raw);action=req['action'];value=req.get('value');result=None
 if action=='choose-monster-type':
  from feedback_update import choose_type
  choose_type(run,value);g.save(run);return json.dumps(state(),ensure_ascii=False)
 if action in ('card-sources','cpu-catalog'):
  import campaign_catalog
  return partial(campaign_catalog.card_sources(value) if action=='card-sources' else campaign_catalog.watch_catalog())
 if action=='pack-inspect':
  from pack_odds import inspect_pack
  return json.dumps(dict(result=inspect_pack(value,storage.profile())),ensure_ascii=False)
 if action.startswith('device-sync-'):
  import progress_sync
  result=progress_sync.dispatch(action[12:],value)
  return json.dumps(dict(**state(),result=result,persist=action!='device-sync-read'),ensure_ascii=False)
 if action=='reward-progress':
  from duel_rewards import progress
  return json.dumps({'result':progress(value['run'],value['events'],g.BY_ID,value.get('victory',False))})
 if action=='import-profile':result=storage.merge_desktop_profile(value,[g.unlock_rule(i)[0] for i in content.PLAYABLE_IDS[2:]])
 elif action=='unlock-cpu-viewer':
  profile=storage.profile();profile['cpu_viewer_unlocked']=True;storage.write(storage.ROOT/'profile.json',profile)
 elif action=='remember-level':
  import challenge_levels
  character=int(value['character']);profile=storage.profile()
  if character not in content.PLAYABLE_IDS or character not in profile['unlocked']:raise ValueError('Choose an unlocked character.')
  level=challenge_levels.validate(character,value['level'])
  profile.setdefault('character_last_levels',{})[str(character)]=level
  storage.write(storage.ROOT/'profile.json',profile)
 elif action=='init':
  run=g.load_run()
 elif action=='select-slot':
  slot=int(value);candidate=g.load_run(slot)
  if not candidate:raise ValueError('This slot has no valid saved run.')
  storage.select_slot(slot);run=candidate
 elif action=='new':
  value=value if isinstance(value,dict) else {'character':int(value)}
  slot=int(value.get('slot',storage.active_slot()));storage.run_path(slot)
  if storage.read(storage.run_path(slot)) and not value.get('replace'):raise ValueError('Confirm before replacing this saved run.')
  candidate=g.new_run(int(value['character']),level=int(value.get('level',0)),variant=int(value.get('variant',0)));candidate['_save_slot']=slot
  g.save(candidate);storage.record_run_start(candidate);storage.select_slot(slot);run=candidate
  profile=storage.profile();profile.setdefault('character_last_levels',{})[str(candidate['character'])]=candidate.get('challenge_level',0);storage.write(storage.ROOT/'profile.json',profile)
 elif action=='secret-champion':
  import secret_challenge
  run=secret_challenge.create(g)
 elif action=='secret-relicless':
  import secret_challenge
  run=secret_challenge.relicless(g,run)
 elif action=='champion':
  import endless
  endless.challenge(g,run)
 elif action=='next-loop':
  import endless
  endless.next_loop(g,run)
 elif action=='auto':g.auto_deck(run)
 elif action=='deselect-all':
  c=content.CHARACTERS[run['character']]
  if c.get('copycat') or c.get('engine_deck'):raise ValueError('This character uses a fixed deck.')
  run['selected']=[]
 elif action=='toggle':
  if content.CHARACTERS[run['character']].get('copycat'):raise ValueError('Copycat uses the borrowed deck plus one Copycat.')
  if content.CHARACTERS[run['character']].get('engine_deck'):raise ValueError('The Dueling Engine uses a fixed deck chosen after victories.')
  index=int(value)
  if index<0 or index>=len(run['pool']):raise ValueError('Unknown card')
  if index in run['selected']:run['selected'].remove(index)
  else:
   cid=run['pool'][index]
   if 'broken_limiter' not in run.get('artifacts',[]) and sum(g.card_identity(run['pool'][i])==g.card_identity(cid) for i in run['selected'])>=3:raise ValueError('Maximum three copies of a card.')
   run['selected'].append(index)
 elif action=='choose':
  if int(value) not in run['routes']:raise ValueError('Unavailable opponent')
  run['opponent']=int(value)
  if content.CHARACTERS[run['character']].get('copycat'):g.copy_deck(run)
  if content.CHARACTERS[run['character']].get('engine_deck'):g.engine_deck(run)
 elif action=='begin':
  g.prepare_duel(run)
  lua=(g.RUNTIME/'puzzles/shadow-run.lua').read_text(encoding='utf8')
  groups={}
  for cid,player,location in re.findall(r'Debug.AddCard\((\d+),(\d),\d,(LOCATION_\w+),',lua):groups.setdefault((int(player),location),[]).append(int(cid))
  info=re.findall(r'Debug.SetPlayerInfo\((\d),(\d+),(\d+),1\)',lua)
  run['mobile_duel']=dict(deck=groups.get((0,'LOCATION_DECK'),[]),enemy=groups.get((1,'LOCATION_DECK'),[]),extra=groups.get((0,'LOCATION_EXTRA'),[]),enemyExtra=groups.get((1,'LOCATION_EXTRA'),[]),lp=int(info[0][1]),enemyLP=int(info[1][1]),draw=int(info[0][2]),enemyDraw=int(info[1][2]),seed=random.randrange(1,2**31),responses=[],passives=passives.script(run))
 elif action=='response':
  wrapped=isinstance(value,dict) and 'response' in value
  response=value['response'] if wrapped else value
  run['mobile_duel']['responses'].append(response)
  save=bool(value.get('checkpoint',False)) if wrapped else True
  if save:g.save(run)
  return partial(persist=save,duelResponse=response)
 elif action=='duel-checkpoint':
  if run and run.get('mobile_duel'):g.save(run)
  return partial(persist=True)
 elif action=='finish':
  result=dict(protocol=1,id=run['duel']['id'],winner=value['winner'],lp=value['lp'],reason=value.get('reason',0),events=value.get('events',[]))
  g.finish_duel(run,result);run.pop('mobile_duel',None)
 elif action=='active-curses':
  import challenge_levels
  result=challenge_levels.active_modifiers(run or {})
 elif action=='peek-deck':
  if 'deck_spyglass' not in run['artifacts'] and run.get('mirror_copy')!='deck_spyglass':raise ValueError('Deck Spyglass is required.')
  opponent=int(value)
  if opponent not in run['routes']:raise ValueError('Unavailable opponent')
  import fallen_collectors
  fallen=fallen_collectors.opponent(run,opponent)
  if fallen:result=fallen['deck']['main']+fallen['deck']['extra']
  else:
   main=g.opponent_deck(run['round'],random.Random(opponent+run['round']*101),opponent,run.get('tutorial_variants',{}).get(str(opponent),0),loop=run.get('loop',0))
   extra=[] if run['round']==0 and not run.get('loop') else content.opponent_record(run['round'],opponent,run.get('loop',0))['extra']
   result=main+extra
 elif action=='cursed-choose':
  import cursed_relics
  cursed_relics.choose(run,str(value))
 elif action=='cursed-reroll':
  import cursed_relics
  cursed_relics.reroll(run)
 elif action=='reveal-opponent':
  import boss_selection
  result=boss_selection.reveal(run,value)
 elif action=='boss-reroll':
  import boss_selection
  result=boss_selection.reroll(g,run)
 elif action=='reward-reroll':
  import reward_slots
  result=reward_slots.reroll(run,value)
  g.update_profile(run)
 elif action=='reward-accept':
  import reward_slots
  reward_slots.accept(run,value)
  g.update_profile(run)
 elif action=='shop-reroll':result=g.reroll_shop(run)
 elif action=='sell-relic':result=g.sell_relic(run,str(value))
 elif action=='buy-many':result=g.buy_many(run,value)
 elif action=='buy':result=g.buy(run,int(value))
 elif action=='reset-progress':storage.reset_progress();run=None
 elif action=='golden-card':
  from golden_cards import choose
  choose(run,value)
 elif action=='settings':storage.write(storage.ROOT/'settings.json',value)
 elif action=='notices':
  p=storage.profile();result=p.pop('achievement_notices',[]);storage.write(storage.ROOT/'profile.json',p)
 elif action=='cheat':
  if value=='heartofthecards':
   p=storage.profile();p['unlock_all']=True;p['unlocked']=content.PLAYABLE_IDS;storage.write(storage.ROOT/'profile.json',p)
  elif value=='reliclessforall':
   p=storage.profile();p['relicless_unlocked']=True;storage.write(storage.ROOT/'profile.json',p)
  elif value=='touchgrass':
   p=storage.profile();p.update(unlock_all=True,unlocked=content.PLAYABLE_IDS,relicless_unlocked=True,testing_all_clears=True,character_levels={str(i):6 for i in content.PLAYABLE_IDS});storage.write(storage.ROOT/'profile.json',p)
  else:raise ValueError('Unknown code')
 else:raise ValueError('Unknown mobile action')
 if action in {'active-curses','peek-deck'}:return partial(result)
 if run and action not in {'import-profile','init','select-slot','new','settings','notices','remember-level','unlock-cpu-viewer','cheat'}:g.save(run)
 if action in {'toggle','auto','deselect-all'}:return partial(persist=True,runPatch={'selected':run['selected'],'last_played_at':run.get('last_played_at')})
 if action=='settings':return partial(persist=True,settings=storage.settings())
 return json.dumps(dict(**state(),result=result),ensure_ascii=False)
