#!/usr/bin/env python3
"""부모 탑10 컷 설계 생성기 — python3 top10_plan.py <ep>  → data/longform/prompts/<ep>.json"""
import json, sys, os
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitconfig
_CFG = kitconfig.load(R)
_STYLE = _CFG['style']
_C = _CFG['characters']
TAIL = _STYLE['tail']
CH = _C['CH']
MOM = _C['MOM']
CHB = CH + ", a small boy with light peach skin and short brown hair,"
FR = _C['FR']
GRAND = _C['GRAND']

def scene(body, cam="The camera holds a gentle slow push in."):
    return f"Clean 3D CG scene of {body} {cam} {TAIL}"
def diagram(body, cam="The camera pushes in slowly."):
    return f"Clean 3D CG diagram of {body} {cam} Absolutely no hands, no humans anywhere in frame — object only. {TAIL}"
def closeup(body, bg="bright sky blue"):
    t = TAIL.replace("on a clean pale cream studio background with a faint soft ground shadow", f"on a plain solid {bg} background filling the whole frame")
    return (f"{body} Tight composition, bright high-contrast light, thick rounded low-poly clay style, the face fills most of the frame, "
            f"a soft empty area at lower left for text, 16:9. The camera holds perfectly still. {t}")
def hero(body):
    return (f"{body} Tight composition, warm bright light, thick rounded low-poly clay style, the subject fills most of the frame, "
            f"a soft empty area at lower left for text, 16:9. The camera holds perfectly still. {TAIL}")

FR2 = _C['FR2']
CHB2 = _C['CHB2']
C2 = _C['C2']; F2 = _C['F2']
MP = _C['MP']
LT = _C['LT']
DAD = _C['DAD']
DP = _C['DP']
GRM = _C['GRM']
TEACH = _C['TEACH']

def TH(a_flow, a_head, panel, b_flow, b_head, doc, c_flow, c_bg, c_head):
    return {'a': {'flow': hero(a_flow), 'head': a_head, 'panel': panel},
            'b': {'flow': hero(b_flow), 'head': b_head, 'doc': {'style': 'paper', 'w': 480, 'rot': -3, 'y': 32, **doc}},
            'c': {'flow': closeup(c_flow, c_bg), 'head': c_head, 'closeup': True}}

PLANS = {}

# ---- 예시 한 편 (fire_water) — 이 블록을 본떠 편마다 추가한다 ----
PLANS['fire_water'] = dict(
    new={
        'Nfw_mom': scene(f"{MP} looking worried at a clay kitchen faucet that gives no water, hands on hips, in a bright clay kitchen."),
        'Nfw_ask': scene(f"{C2} with wide shocked eyes and hands on his cheeks in a bright clay kitchen."),
        'Nfw_friend': scene(f"{F2} hugging himself and pretending to shiver with a silly grin next to {C2} in a bright clay classroom."),
        'Nfw_water': diagram("a gentle clay stream of blue water flowing in soft wavy ripples across a cream surface."),
        'Nfw_pipe': diagram("a clean clay water pipe running along a wall to a small faucet, blue clay water flowing out into a bowl."),
        'Nfw_city': diagram("a bright clay city skyline with tall buildings and a round clay crown floating above it, on a cream background."),
        'Nfw_updown': diagram("a cross-section of a clay house: a blue clean water pipe entering from above and a grey pipe leaving below, arrows of flow."),
        'Nfw_fire': diagram("a small warm clay campfire with soft rounded orange flames flickering gently on a cream surface."),
        'Nfw_ext': diagram("a small red clay fire extinguisher spraying a soft cloud onto tiny clay flames that shrink and vanish."),
        'Nfw_tummy': scene(f"{C2} patting his round tummy happily after a meal at a bright clay table."),
        'Nfw_fixed': scene(f"{C2} cheering as blue clay water flows from the kitchen faucet again, {MP} clapping, in a bright clay kitchen."),
    },
    map={1:'Nfw_mom',2:'Nfw_ask',3:'Nfw_friend',4:'Nfw_mom',5:'Nfw_pipe',6:'Nfw_pipe',7:'Nfw_water',8:'Nfw_pipe',9:'Nfw_pipe',10:'Nfw_city',
         11:'Nfw_ask',12:'Nfw_city',13:'Nfw_updown',14:'Nfw_updown',15:'Nfw_updown',16:'Nfw_friend',17:'Nfw_fire',18:'Nfw_fire',19:'Nfw_ext',20:'Nfw_tummy',
         21:'Nfw_tummy',22:'Nfw_fire',23:'Nfw_water',24:'Nfw_ext',25:'Nfw_fixed',26:'Nfw_fixed'},
    thumb=TH(f"Medium close-up of {C2} with wide shocked eyes and hands on his cheeks, placed toward the right side of the frame.",
             [['수도가 얼면', 88, 'WHT'], ['서울이 얼어?', 120, 'BOX']], ['水道', '수도', 'right'],
             f"Medium close-up of {MP} holding a small clay faucet with a worried smile, {LT}",
             [['오늘 아침', 88, 'WHT'], ['수도가 얼었대', 120, 'BOX']], {'title': '아파트 안내문', 'rows': ['한파로 수도 동결', '복구 오후 2시', '세대 내 물 받아 두기'], 'hl': '한파로 수도 동결'},
             f"Extreme close-up of the face of {C2} pretending to shiver with chattering teeth and squeezed eyes, tiny clay snowflakes around, the face filling sixty percent of the frame on the right side.", "bright sky blue",
             [['서울이', 110, 'WHT'], ['얼었다고?', 140, 'BOX']]),
)


# ---- 예시 2 (일반 주제, examples/generic_episode.json = rainbow) — B절 튜토리얼이 이 블록을 쓴다 ----
PLANS['rainbow'] = dict(
    new={
        'Nrb_ask': scene(f"{C2} pointing up at a soft pastel rainbow through a bright clay window and asking {MP} with wide curious eyes, in a bright clay living room after rain."),
        'Nrb_mom': scene(f"{MP} smiling and holding up one finger as she explains, beside a bright clay window with tiny raindrops."),
        'Nrb_friend': scene(f"{F2} counting on his fingers with an excited grin next to {C2} on a bright clay playground with puddles."),
        'Nrb_drops': diagram("tiny round clay water droplets floating gently in warm sunlight against a soft blue sky."),
        'Nrb_light': diagram("a warm beam of clay sunlight entering a big round clear clay droplet and fanning out into soft rainbow stripes."),
        'Nrb_bend': diagram("a single clay light beam bending smoothly as it passes through a big round clear clay droplet, stripes spreading apart."),
        'Nrb_bounce': diagram("a rainbow-striped clay beam bouncing off the inside wall of a big round clear droplet and coming back out toward the viewer."),
        'Nrb_angle': diagram("a small clay sun on the left, a big clear droplet on the right, and a soft glowing arc between them over green clay hills."),
        'Nrb_arc': diagram("a wide soft pastel rainbow arc over small green clay hills and a tiny clay house, gentle clouds drifting."),
        'Nrb_walk': scene(f"{C2} walking toward a pastel rainbow on a bright clay meadow while the rainbow gently shifts away, puzzled smile."),
        'Nrb_look': scene(f"{C2} and {F2} standing on a bright clay hill after rain, looking up together at a pastel rainbow and cheering."),
    },
    map={1:'Nrb_ask',2:'Nrb_mom',3:'Nrb_friend',4:'Nrb_mom',5:'Nrb_light',6:'Nrb_drops',7:'Nrb_light',8:'Nrb_ask',9:'Nrb_bend',10:'Nrb_friend',
         11:'Nrb_bounce',12:'Nrb_mom',13:'Nrb_angle',14:'Nrb_ask',15:'Nrb_friend',16:'Nrb_arc',17:'Nrb_walk',18:'Nrb_walk',19:'Nrb_mom',20:'Nrb_bend',
         21:'Nrb_bounce',22:'Nrb_arc',23:'Nrb_look',24:'Nrb_look'},
    thumb=TH(f"Medium close-up of {C2} pointing up with a wide curious smile, a soft pastel rainbow behind, placed toward the right side of the frame.",
             [['무지개는', 88, 'WHT'], ['왜 생겨?', 150, 'BOX']], ['무지개', '빛의 비밀', 'right'],
             f"Medium close-up of {MP} holding a small clear clay droplet up to the light with a warm smile, {LT}",
             [['비 그친 뒤', 88, 'WHT'], ['하늘에?', 150, 'BOX']], {'title': '과학 관찰 일기', 'rows': ['비 온 뒤 하늘 보기', '무지개 색 세기', '해 반대쪽 찾기'], 'hl': '해 반대쪽 찾기'},
             f"Extreme close-up of the face of {C2} with big sparkling eyes reflecting tiny rainbow stripes, mouth open in wonder, the face filling sixty percent of the frame on the right side.", "bright sky blue",
             [['일곱 색이', 100, 'WHT'], ['숨어 있다?', 140, 'BOX']]),
)

def build(ep):
    p = PLANS[ep]
    out = {'id': ep, 'scratch_dir': p.get('scratch', f'scratch/flow_{ep}'), 'clips_dir': p.get('clips', ep), 'new_prompts': p['new'],
           'map': {str(k): v for k, v in p['map'].items()}, 'thumb': p['thumb']}
    out = json.loads(json.dumps(out).replace(',,', ','))
    json.dump(out, open(f'{R}/data/longform/prompts/{ep}.json', 'w'), ensure_ascii=False, indent=2)
    print(ep, len(p['new']), 'new clips')

if __name__ == '__main__':
    for e in sys.argv[1:]: build(e)
