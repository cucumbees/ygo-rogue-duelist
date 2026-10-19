"""Build the single "Modern Collection" pack (every post-2005 card that can actually run).

Rules
  * Card pool: runtime/expansions/cards.cdb (official cards only; no Rush, Skills, anime or tokens).
  * Cards already in data/era-cards.json (or sharing a name with one) stay in their original packs.
  * Unscripted cards are NOT added. A card needs a script when it is a Spell/Trap or has an effect
    (type bit 0x20). Vanilla monsters (Normal / Fusion / Synchro / Xyz / Link / Pendulum Normal)
    need no script and are included.
  * Scripts must exist in android/web/scripts.json (the bundle the web/Android engine really runs).
  * If android/web/modern-script-errors.json exists (written by android/test_modern_scripts.mjs),
    every card listed there is dropped, so only cards whose scripts load cleanly are included.

Outputs
  data/modern-cards.json          card metadata (same schema as era-cards.json + "modern": true)
  data/modern-pack.json           the single MODERN-ALL pack (merged into PACKS by content.py)
  android/web/engine-data.json    adds engine rows for the new cards and fixes Link rows
  assets/packs/MODERN-ALL.jpg     placeholder pack art (generated if missing)

Run:  python tools/build_modern_pack.py
"""
import json, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'android/web'
PACK_ID = 'MODERN-ALL'

T_MONSTER, T_SPELL, T_TRAP, T_NORMAL, T_EFFECT = 0x1, 0x2, 0x4, 0x10, 0x20  # NORMAL here = 0x10 flag
T_FUSION, T_RITUAL, T_SPIRIT, T_UNION, T_GEMINI, T_TUNER = 0x40, 0x80, 0x200, 0x400, 0x800, 0x1000
T_SYNCHRO, T_TOKEN, T_FLIP, T_TOON, T_XYZ, T_PENDULUM, T_LINK = 0x2000, 0x4000, 0x200000, 0x400000, 0x800000, 0x1000000, 0x4000000
EXTRA_MASK = T_FUSION | T_SYNCHRO | T_XYZ | T_LINK

RACES = {1: 'Warrior', 2: 'Spellcaster', 4: 'Fairy', 8: 'Fiend', 16: 'Zombie', 32: 'Machine', 64: 'Aqua', 128: 'Pyro',
         256: 'Rock', 512: 'Winged Beast', 1024: 'Plant', 2048: 'Insect', 4096: 'Thunder', 8192: 'Dragon', 16384: 'Beast',
         32768: 'Beast-Warrior', 65536: 'Dinosaur', 131072: 'Fish', 262144: 'Sea Serpent', 524288: 'Reptile',
         1048576: 'Psychic', 2097152: 'Divine-Beast', 4194304: 'Creator God', 8388608: 'Wyrm', 16777216: 'Cyberse',
         33554432: 'Illusion'}
ATTRS = {1: 'EARTH', 2: 'WATER', 4: 'FIRE', 8: 'WIND', 16: 'LIGHT', 32: 'DARK', 64: 'DIVINE'}


def type_name(t):
    if t & T_SPELL: return 'Spell Card'
    if t & T_TRAP: return 'Trap Card'
    eff = bool(t & T_EFFECT)
    for bit, label in [(T_LINK, 'Link Monster'), (T_XYZ, 'XYZ Monster'), (T_SYNCHRO, 'Synchro Monster'), (T_FUSION, 'Fusion Monster')]:
        if t & bit: return label
    if t & T_PENDULUM: return 'Pendulum Effect Monster' if eff else 'Pendulum Normal Monster'
    if t & T_RITUAL: return 'Ritual Effect Monster' if eff else 'Ritual Monster'
    for bit, label in [(T_FLIP, 'Flip Effect Monster'), (T_SPIRIT, 'Spirit Monster'), (T_UNION, 'Union Effect Monster'),
                       (T_TOON, 'Toon Monster'), (T_GEMINI, 'Gemini Monster')]:
        if t & bit: return label
    return 'Effect Monster' if eff else 'Normal Monster'


def subtype(t):
    if t & T_SPELL:
        for bit, label in [(0x80, 'Ritual'), (0x10000, 'Quick-Play'), (0x20000, 'Continuous'), (0x40000, 'Equip'), (0x80000, 'Field')]:
            if t & bit: return label
        return 'Normal'
    for bit, label in [(0x20000, 'Continuous'), (0x100000, 'Counter')]:
        if t & bit: return label
    return 'Normal'


def setcodes(value):
    out = []
    while value:
        if value & 0xFFFF: out.append(value & 0xFFFF)
        value >>= 16
    return out


def engine_row(code, alias, setcode, typ, atk, defense, level_raw, race, attr):
    """Mirror EDOPro's card reader: decode Pendulum scales and Link markers."""
    lscale = rscale = marker = 0
    level = level_raw & 0xFF
    if typ & T_PENDULUM:
        lscale, rscale = (level_raw >> 24) & 0xFF, (level_raw >> 16) & 0xFF
    if typ & T_LINK:
        marker, defense = defense, 0
    return dict(code=code, alias=alias, setcodes=setcodes(setcode), type=typ, level=level, attribute=attr, race=str(race),
                attack=atk, defense=defense, lscale=lscale, rscale=rscale, link_marker=marker)


def needs_script(typ):
    return bool(typ & (T_SPELL | T_TRAP | T_EFFECT))


def main():
    era = json.loads((ROOT / 'data/era-cards.json').read_text(encoding='utf8'))
    era_ids = {c['id'] for c in era}
    era_names = {c['name'] for c in era}
    # Anything already obtainable elsewhere stays there: custom cards, opponent exceptions and every card
    # referenced by an existing pack (e.g. WC4-20's exclusive Spell).
    sys.path.insert(0, str(ROOT))
    import custom_cards
    for c in custom_cards.CARDS:
        era_ids.add(c['id']); era_names.add(c['name'])
    for c in json.loads((ROOT / 'data/opponent-card-exceptions.json').read_text(encoding='utf8')):
        era_ids.add(c['id']); era_names.add(c['name'])
    base_packs = json.loads((ROOT / 'data/packs.json').read_text(encoding='utf8'))
    custom_cards.install_packs(base_packs)  # adds custom boosters such as WC4-20
    for pk in base_packs:
        for key in ('common', 'rare', 'starter_support', 'rare_display'):
            era_ids.update(pk.get(key, []))
    scripts = json.loads((WEB / 'scripts.json').read_text(encoding='utf8'))
    have_script = {int(k[1:-4]) for k in scripts if re.fullmatch(r'c\d+\.lua', k)}
    bad = set()
    err_path = WEB / 'modern-script-errors.json'
    if err_path.exists():
        bad = set(json.loads(err_path.read_text(encoding='utf8')))

    db = sqlite3.connect(ROOT / 'runtime/expansions/cards.cdb')
    cols = ['id', 'alias', 'setcode', 'type', 'atk', 'def', 'level', 'race', 'attribute']
    rows = db.execute('SELECT d.id,d.alias,d.setcode,d.type,d.atk,d.def,d.level,d.race,d.attribute,'
                      't.name,t.desc,t.str1,t.str2,t.str3,t.str4,t.str5,t.str6,t.str7,t.str8,t.str9,t.str10,t.str11,'
                      't.str12,t.str13,t.str14,t.str15,t.str16 FROM datas d JOIN texts t USING(id)').fetchall()

    cards, engine, skipped = [], {}, dict(era=0, token_or_alt=0, unscripted=0, script_error=0)
    for row in rows:
        cid, alias, sc, typ, atk, de, lv, race, attr, name, desc = row[:11]
        strings = [s or '' for s in row[11:27]]
        if cid in era_ids or name in era_names:
            skipped['era'] += 1; continue
        if cid >= 100000000 or alias or typ & T_TOKEN:
            skipped['token_or_alt'] += 1; continue
        if needs_script(typ) and cid not in have_script:
            skipped['unscripted'] += 1; continue
        if cid in bad:
            skipped['script_error'] += 1; continue
        e = engine_row(cid, alias, sc, typ, atk, de, lv, race, attr)
        engine[str(cid)] = e
        monster = bool(typ & T_MONSTER)
        cards.append(dict(
            id=cid, name=name, desc=desc, type=type_name(typ),
            race=RACES.get(race, 'Normal') if monster else subtype(typ),
            attribute=ATTRS.get(attr, '') if monster else '',
            level=e['level'] if monster else 0, atk=max(atk, 0) if monster else 0,
            defense=max(e['defense'], 0) if monster else 0,
            date='2006-01-01', modern=True,
            sets=[dict(name='Modern Collection', rarity='Common')],
            image=f'https://images.ygoprodeck.com/images/cards/{cid}.jpg', data=e, strings=strings))

    cards.sort(key=lambda c: c['id'])
    # Rare slot: everything that lives in the Extra Deck, plus Pendulum monsters.
    rare = [c['id'] for c in cards if c['data']['type'] & (EXTRA_MASK | T_PENDULUM)]
    rare_set = set(rare)
    common = [c['id'] for c in cards if c['id'] not in rare_set]

    (ROOT / 'data/modern-cards.json').write_text(json.dumps(cards, ensure_ascii=False, separators=(',', ':')), encoding='utf8')

    # Kept in its own file so data/packs.json (hand-maintained, CRLF) is untouched; content.py merges it in.
    pack = dict(id=PACK_ID, name='Modern Collection', region='EN', code='MOD', date='2006-01-01', image='',
                common=common, rare=rare, size=9, rare_display=rare,
                rarities={str(i): ['Common'] for i in common} | {str(i): ['Rare'] for i in rare},
                rarity_source='Generated by tools/build_modern_pack.py (Extra Deck + Pendulum = Rare slot)', modern=True)
    (ROOT / 'data/modern-pack.json').write_text(json.dumps(pack, separators=(',', ':')), encoding='utf8')

    # engine-data: add new cards and repair every Link row (marker lives in DEF in the cdb).
    ed_path = WEB / 'engine-data.json'
    ed = json.loads(ed_path.read_text(encoding='utf8'))
    fixed = 0
    for k, v in ed.items():
        if v['type'] & T_LINK and v['link_marker'] == 0 and v['defense'] > 0:
            v['link_marker'], v['defense'] = v['defense'], 0; fixed += 1
    ed.update(engine)
    ed_path.write_text(json.dumps(ed, ensure_ascii=False), encoding='utf8')

    art = ROOT / f'assets/packs/{PACK_ID}.jpg'
    if not art.exists():
        try:
            from PIL import Image, ImageDraw
            im = Image.new('RGB', (420, 600), (24, 28, 52)); d = ImageDraw.Draw(im)
            for y in range(600): d.line([(0, y), (420, y)], fill=(24 + y // 12, 28 + y // 20, 52 + y // 6))
            d.text((120, 280), 'MODERN\nCOLLECTION', fill=(240, 220, 150))
            im.save(art, quality=88)
        except Exception as exc:
            print('pack art skipped:', exc)

    print(f'{PACK_ID}: {len(cards)} cards ({len(common)} common / {len(rare)} rare)')
    print('skipped:', skipped, '| Link rows repaired in engine-data:', fixed)


if __name__ == '__main__':
    sys.exit(main())
