#!/usr/bin/env python3
"""부모 탑10 컷 설계 생성기 — python3 top10_plan.py <ep>  → data/longform/prompts/<ep>.json"""
import json, sys, os
R = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..')))
TAIL = ("Bright colorful low-poly 3D clay-like models with soft rounded edges, warm pastel palette of cream, sky blue, mint green and soft coral, "
        "on a clean pale cream studio background with a faint soft ground shadow. Soft warm studio lighting from upper left, gentle ambient occlusion, "
        "no harsh shadows. Clean playful explainer animation look for children, not photorealistic, not cinematic, not dark. "
        "No numbers, no lettering, no text, no captions, no watermark, no UI, no logo.")
CH = "a round clay child with a simple round face, two small dark eyes and rosy cheeks, wearing a blue shirt"
MOM = ("a taller clay parent figure wearing a mint green cardigan, a friendly clay mother with a simple round human face, "
       "short black bob hair, two small dark eyes and rosy cheeks")
CHB = CH + ", a small boy with light peach skin and short brown hair,"
FR = "a smiling clay classmate in a coral shirt"
GRAND = "a kind clay grandfather figure with short white hair and a soft grey vest"

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

FR2 = "a smiling clay classmate in a coral shirt with short black hair"
CHB2 = CH + ", a small boy with light peach skin and a full head of short brown hair,"
C2 = CHB2; F2 = FR2
MP = MOM + " with light peach skin"
LT = "placed at the left third of the frame, plain soft cream wall filling the whole right half."
DAD = "a taller clay parent figure wearing a sky blue cardigan, a friendly clay father with a simple round human face, short black hair, two small round eyes and rosy cheeks"
DP = DAD + " with light peach skin"
GRM = "a kind clay grandmother with short white hair in a soft pink cardigan"
TEACH = "a friendly clay teacher figure in a light yellow blouse with black hair in a low bun and round glasses"

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


def build(ep):
    p = PLANS[ep]
    out = {'id': ep, 'scratch_dir': p.get('scratch', f'scratch/flow_{ep}'), 'clips_dir': p.get('clips', ep), 'new_prompts': p['new'],
           'map': {str(k): v for k, v in p['map'].items()}, 'thumb': p['thumb']}
    out = json.loads(json.dumps(out).replace(',,', ','))
    json.dump(out, open(f'{R}/data/longform/prompts/{ep}.json', 'w'), ensure_ascii=False, indent=2)
    print(ep, len(p['new']), 'new clips')

if __name__ == '__main__':
    for e in sys.argv[1:]: build(e)
