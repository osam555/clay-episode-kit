#!/usr/bin/env python3
"""kit.config.json 로더 — 이 kit 을 다른 주제/캐릭터/브랜드로 쓸 때 코드를 고치지 않고 여기서 바꾼다.

load() 는 다음을 이 순서로 합쳐 dict 하나를 돌려준다 (뒤가 앞을 덮어씀):
  1) DEFAULTS  — 이 파일에 박힌 값. 지금 알리랑(clay 캐릭터·한자 어원) 그대로다 —
     kit.config.json 이 아예 없어도 예전과 똑같이 돈다(바이트 단위로 같아야 한다).
  2) kit.config.example.json — 저장소에 있으면 참고용으로 얹는다(진짜 설정이 없을 때의 대체).
  3) kit.config.json — ALLIRANG_ROOT(없으면 cwd)에 있으면 이게 최종.

사용:
  from kitconfig import load
  cfg = load()
  cfg['characters']['C2']   # 캐릭터 문구
  cfg['brand']['site_url']  # 사이트 URL
"""
import json, os, copy

def _root():
    return os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ---- 기본값 — top10_plan.py / CHARACTERS.json / 각 스크립트에 박혀 있던 값을 그대로 옮겼다 ----
_TAIL = ("Bright colorful low-poly 3D clay-like models with soft rounded edges, warm pastel palette of cream, sky blue, mint green and soft coral, "
         "on a clean pale cream studio background with a faint soft ground shadow. Soft warm studio lighting from upper left, gentle ambient occlusion, "
         "no harsh shadows. Clean playful explainer animation look for children, not photorealistic, not cinematic, not dark. "
         "No numbers, no lettering, no text, no captions, no watermark, no UI, no logo.")
_CH = "a round clay child with a simple round face, two small dark eyes and rosy cheeks, wearing a blue shirt"
_MOM = ("a taller clay parent figure wearing a mint green cardigan, a friendly clay mother with a simple round human face, "
        "short black bob hair, two small dark eyes and rosy cheeks")
_FR = "a smiling clay classmate in a coral shirt"
_GRAND = "a kind clay grandfather figure with short white hair and a soft grey vest"
_FR2 = "a smiling clay classmate in a coral shirt with short black hair"
_CHB2 = _CH + ", a small boy with light peach skin and a full head of short brown hair,"
_DAD = ("a taller clay parent figure wearing a sky blue cardigan, a friendly clay father with a simple round human face, "
        "short black hair, two small round eyes and rosy cheeks")

DEFAULTS = {
    "topic": {
        # "generic" — 임의 주제(과학·역사·일상·영단어 등), 카드는 {title, subtitle} 키워드 쌍.
        # "hanja"   — 한자 어원(알리랑 기본값), 카드는 {한자, 훈음}. hanja_check/northstar_check 의 기초한자 채점이 실제로 적용된다.
        # 카드에 한자 글자가 하나도 없으면(hz() 가 빈 리스트) 검사기가 자동으로 "순우리말/generic" 취급을 한다 —
        # 이 필드는 그 자동판정을 명시적으로 남기는 문서용 스위치다.
        "kind": "generic",
        "card_style": "keyword",
    },
    "brand": {
        "name": "알리랑",
        "wordmark_png": "remotion/public/allirang-wordmark.png",
        "logo_png": "assets/brand/allirang-logo.png",
        "intro_mp4": "assets/intro_msg.mp4",
        "outro_mp4": "assets/ending_narr.mp4",
        "site_url": "https://allirang.com/word",
        "hashtags": ["#알리랑", "#한자", "#어원", "#문해력"],
        "description_footer": "📖 알리랑 — 한자 어원으로 배우는 우리말",
    },
    "channels": {
        "allirang": {"studio_tab_hint": None, "channel_id": None, "playlist": None,
                      "token": ".youtube_token.json", "label": "알리랑 (브랜드계정)", "expect_url": "@allirang"},
        "daechung": {"studio_tab_hint": None, "channel_id": None, "playlist": "PLVkZur3-_ysc",
                     "token": ".youtube_token_daechung.json", "label": "대충영어 (seungjong555)", "expect_url": None},
        "johnwu571": {"studio_tab_hint": None, "channel_id": None, "playlist": None,
                      "token": ".youtube_token_johnwu571.json", "label": "개인 채널 (배포용 아님)", "expect_url": "@johnwu571"},
    },
    "default_channel": "allirang",
    "publish_channels": ["allirang", "daechung"],
    "style": {
        "tail": _TAIL,
        "palette": ["cream", "sky blue", "mint green", "soft coral"],
        "negative": ["not photorealistic", "not cinematic", "not dark", "no text", "no watermark"],
    },
    "characters": {
        "CH": _CH,
        "MOM": _MOM,
        "FR": _FR,
        "GRAND": _GRAND,
        "FR2": _FR2,
        "CHB2": _CHB2,
        "C2": _CHB2,
        "F2": _FR2,
        "MP": _MOM + " with light peach skin",
        "LT": "placed at the left third of the frame, plain soft cream wall filling the whole right half.",
        "DAD": _DAD,
        "DP": _DAD + " with light peach skin",
        "GRM": "a kind clay grandmother with short white hair in a soft pink cardigan",
        "TEACH": "a friendly clay teacher figure in a light yellow blouse with black hair in a low bun and round glasses",
    },
    "language": {"narration": "ko", "on_screen": "ko"},
    "tts": {
        "provider": "typecast",
        "voices": {"narrator": None, "child": None, "adult": None, "friend": None},
    },
    "thumbnail": {
        "headline_font": "remotion/public/fonts/BlackHanSans-Regular.ttf",
        "fallback_font": "remotion/public/fonts/NotoSansCJKkr-Black.otf",
        "box_color": "#FFD600",
        "wordmark_pill": True,
    },
}


def _deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read(path):
    try:
        if os.path.exists(path):
            return json.load(open(path, encoding='utf-8'))
    except Exception:
        pass
    return None


def load(root=None):
    root = root or _root()
    cfg = copy.deepcopy(DEFAULTS)
    example = _read(f'{root}/kit.config.example.json')
    if example:
        cfg = _deep_merge(cfg, example)
    real = _read(f'{root}/kit.config.json')
    if real:
        cfg = _deep_merge(cfg, real)
    return cfg


if __name__ == '__main__':
    print(json.dumps(load(), ensure_ascii=False, indent=2))
