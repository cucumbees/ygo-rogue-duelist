import sys,json,random,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import campaign as g,content,storage,approved_relics as ar,cursed_relics as cr,boss_selection as bs
base=Path(tempfile.mkdtemp(prefix='jar-relics-',dir=ROOT/'temp'));storage.ROOT=base;g.SAVE=base/'run.json'
r=g.new_run(0,random.Random(7));r.update(stage='shop',gold=1000);r['artifacts']+=['dice_jar','morphing_jar_2','cyber_jar'];g.restock(r,random.Random(2))
assert g.reroll_price(r)==0
assert g.reroll_shop(r,random.Random(3))==0 and r['gold']==1000
r=json.loads(json.dumps(r));assert g.reroll_price(r)==10
assert g.reroll_shop(r,random.Random(4))==10
personal='DRAFT-'+content.CHARACTERS[0]['name'].upper().replace(' ','-')
assert any(x['kind']=='pack' and x['id']==personal and not x['sold'] for x in r['shop']),personal
r['round']=1;assert g.reroll_price(r)==0
cr.create_offer(r,random.Random(8));assert r['cursed_offer']['rerolls_left']==2
cr.reroll(r,random.Random(9));assert r['cursed_offer']['rerolls_left']==1
cr.reroll(r,random.Random(10));assert r['cursed_offer']['rerolls_left']==0
try:cr.reroll(r);raise AssertionError('Third reroll allowed')
except ValueError:pass
r.pop('cursed_offer');g.routes(r,random.Random(4));r['stage']='draft';a,b=r['routes'][:2];gold=r['gold'];assert bs.reveal(r,a)==0 and r['gold']==gold;assert bs.reveal(r,a)==0;assert bs.reveal(r,b)==15
r['round']=2;g.routes(r,random.Random(6));assert bs.price(r)==0;assert bs.reroll(g,r,random.Random(7))==0;assert bs.price(r)==30
r['round']=5;g.routes(r,random.Random(8));assert bs.price(r)==0
r['challenge_level']=-1;assert g.reroll_price(r)>0 and bs.price(r)>0
print('PASS Jar prices, free-use persistence/reset, fresh personal pack, two cursed rerolls, reveals, boss rerolls, disabled relics')

