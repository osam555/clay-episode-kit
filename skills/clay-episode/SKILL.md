---
name: clay-episode
description: 알리랑 클레이 애니 롱폼 1편(+45초 쇼츠+썸네일 3종)을 대본→더빙→컷 계획→Flow 생성→조립→QA→R2→유튜브까지 만드는 절차. Windows/macOS 공통.
---

# 클레이 애니 편 제작 (2026-09-25 정본)

한 편 = 롱폼 16:9(2~3분, 인트로·엔딩 포함) + 세로 쇼츠 45초(첫 장면, 제목띠·로고) + 썸네일 3종(a/b/c).
소요: 편당 Flow 크레딧 ≈110~130(6초 컷 10~12개 × 10, 썸네일 이미지는 무료), 사람 시간 ≈20분(대기 제외).

## 0. 준비물 (Windows)

| 것 | 설치 |
|---|---|
| Python 3.12+ | python.org 설치 프로그램, "Add python.exe to PATH" 체크 |
| `pip install -r requirements.txt` | pillow·numpy·google-auth(-oauthlib)·google-api-python-client |
| Node 20+ | nodejs.org, 그 다음 `npm install` (Playwright 등) |
| Playwright 브라우저 | `npx playwright install chromium` (Aside 폴백용 — 8절) |
| ffmpeg/ffprobe | gyan.dev 빌드 다운로드 → 압축 풀고 `bin/` 을 PATH 에 등록 |
| esbuild | `npm install` 이 `node_modules/@esbuild/win32-x64/esbuild.exe` 를 깐다. `bake.mjs` 가 자동으로 찾지만 안 되면 `$env:ESBUILD` 로 그 경로를 직접 준다 |
| Typecast 키 | `.env.local` 에 `TYPECAST_API_KEY=...` — 절대 출력·커밋 금지 |
| Cloudflare R2 | `npx wrangler login` 1회 |
| `.sh` 스크립트 | Windows 는 `.sh` 대신 같은 이름의 `.py` 를 쓴다(`prep_more.py`, `drain_uploads.py`) — 이 kit 은 둘 다 있다 |
| Drive 재사용 라이브러리 | Google Drive 데스크톱 앱 로그인 후 `$env:DRIVE_LIB = "G:\My Drive\allirang-library"` |

macOS 는 brew 로 Python/Node/ffmpeg, `.sh` 는 zsh 로 그대로 돈다.

### Aside 설치 (Flow·YouTube Studio 브라우저 자동화 — 1순위) — 다운로드: https://aside.com/download (macOS·Windows, Windows 정식판 2026-09-14 출시; 무료 플랜으로 `aside repl` 사용 가능)

이 kit 의 브라우저 자동화는 **Aside 를 기본으로** 쓴다(`scripts/browser.py` 가 PATH 에서 `aside` 를 먼저 찾는다). Playwright 러너(8절)는 Aside 를 못 쓸 때의 폴백이다.

1. Aside 앱을 설치한다 — 앱 다운로드 페이지 주소는 Aside 앱 안의 Help 메뉴나 `aside --help`/`aside guide` 출력에서 확인한다(버전마다 바뀔 수 있어 여기 박아 두지 않는다). Windows 빌드가 있는지도 그 페이지에서 확인 — 없으면 8절의 Playwright 러너로 간다.
2. `aside login` 으로 로그인.
3. `aside account` 로 쓸 계정을 고른다.
4. Aside 안에서 탭 두 개를 연다 — `flow.google.com`(Flow)과 YouTube Studio 채널 페이지(채널마다 하나) — 열린 탭에서 Google 로그인을 한 번 해 둔다.
5. 탭 id 를 얻는다:
   ```bash
   aside repl 'console.log(JSON.stringify((await listBrowserTabs()).map(t=>[t.targetId,t.url])))'
   ```
   출력에서 Flow 탭 id 를 `FLOW_TAB`, Studio 채널 탭 id 를 `YT_CHANNELS` 의 값으로 쓴다(1절 참고, 형식은 `{"<채널키>": ["<탭id>", "<채널ID UC…>", "<재생목록 이름>"]}`).

환경변수(선택): `ALLIRANG_ROOT`(저장소 경로, 기본은 스크립트 위치에서 추정), `FLOW_WORK`(작업 파일 폴더, 기본 `scratch/flow_tools`), `FLOW_TAB`(Aside 의 Flow 탭 id), `YT_CHANNELS`, `DRIVE_LIB`.
스크립트는 전부 `scripts/` 에 있다. Windows 는 `/tmp/...` 경로를 쓰는 곳(큐·로그)에 `FLOW_WORK` 아래 경로를 주면 된다(PowerShell 예: `$env:FLOW_WORK = "$PWD\scratch\flow_tools"`).

### 편 하나의 저장소 레이아웃

```
data/longform/<key>.json          정본 — script_v2.lines(대사) · tts.voices · images[] · yt_meta 등. 스키마 예시: examples/sample_episode.json
data/longform/prompts/<key>.json  top10_plan.py 가 생성하는 컷 계획(Flow 프롬프트)
scratch/flow_<key>/                작업 파일 — n01.wav…(더빙), lines.json, <key>_short.mp4
assets/flow/<key>/                 Flow 가 뱉은 컷 mp4/이미지, thumb/{a,b,c}.jpg
assets/longform/<key>/thumb/       make_thumb.py 산출물(final-a/b/c.png)
remotion/out/<key>_deploy.mp4      flow_assemble.py --deploy 산출물
```

## A. 새 주제·캐릭터로 시작하기

이 kit 은 원래 알리랑(한자 어원)용으로 만들었지만, `kit.config.json` 하나로 다른 주제·캐릭터·브랜드에도 그대로 쓴다.
모든 스크립트가 캐릭터 문구·스타일 꼬리·채널·사이트 URL·해시태그를 `kit.config.json`(없으면 `kit.config.example.json`, 그것도 없으면 `scripts/kitconfig.py` 의 기본값=알리랑)에서 읽는다.

1. **`python3 scripts/new_project.py` 먼저 돌린다.** 브랜드 이름·사이트 URL·해시태그·나레이션 언어·캐릭터 역할(아이/엄마/아빠/친구/할아버지/할머니/선생님)을 물어보고
   `kit.config.json` 을 쓰고 `data/longform`·`assets/brand`·`scratch` 등 필요한 폴더를 만든다. 브랜드 에셋(워드마크·인트로)이 없으면 Pillow·ffmpeg 로 자리표시자를 만들어 준다(없으면 경고만 하고 건너뛴다).
   질문 없이 자리표시자 값으로 바로 돌리려면 `--defaults`.

2. **`kit.config.json` 을 손으로 다듬는다.** 프롬프트가 실제로 참조하는 건 `characters` 칸뿐이다 — 역할마다 시각적 특징(옷 색·머리·표정)을 고정 문구로 써 둔다.
   같은 인물이 편·컷마다 다르게 나오면 안 되므로, `CH`(아이)·`MOM`·`DAD`·`FR`(친구)·`GRAND`·`GRM`·`TEACH` 같은 역할 키에 **항상 같은 문구**를 쓴다. `channels`(유튜브 채널 ID·토큰 경로)·`tts.voices`(Typecast 보이스 id)도 여기서 채운다.

3. **대본을 쓴 다음 §1 로 간다.** 대본 템플릿은 아래 구조를 쓴다 — 롱폼 파일럿들에서 잘 먹힌 순서다.

### 대본 템플릿 (23~28줄, 나레이션 ≤2:30)

1. 아이의 엉뚱한 질문(훅) 1줄
2. 어른/친구 반응 2줄
3. 「같이 볼까요?」 1줄
4. 글자 풀이 1~2줄 「…라고 풀어요」 — **한자 편에만 쓰는 선택 단계다.** 한자가 아닌 주제면 통째로 뺀다.
5. 낱말 3~6개, 각 1줄 「A. B 에 C. 뜻.」 형식 + 아이·친구 리액션을 사이사이에
6. 반전/주의 1~2줄
7. 복습 나열 2줄 「…, …. 다 X.」
8. 콜백 마무리 1줄

화자 태그는 `[[child]]` `[[adult]]` `[[friend]]` 를 줄 앞에 붙인다(목소리를 고르는 표시일 뿐, 자막에는 안 나간다 — `flow_assemble.py` 가 뗀다).
`data/longform/<key>.json` 의 `script_v2.lines` 에 `{ "ch": 0, "i": 1, "text": "[[child]] …", "g": 1 }` 형식으로 넣는다(`examples/sample_episode.json` 참고).

썸네일 `thumb.a.panel`(우상단 대각 재료)도 기본은 **키워드판**(주제어 두 줄, 예 `['무지개','빛의 비밀','right']`)이다 — 한자판(`['漢字','훈음','right']`)은 `topic.kind: "hanja"` 일 때의 변형일 뿐, 형식(세 값: 첫 줄·둘째 줄·`"right"`)은 같다.

### 카드(한자판) 칸 — 한자 아닌 주제는 이렇게

카드는 `scratch/flow_<key>/cards.json`(또는 `prompts/<key>.json` 의 `cards_full`)의 `CARD` 에 `{ "<문장번호 g>": ["첫째줄", "둘째줄"] }` 형식으로 들어간다 —
`flow_assemble.py` 가 `CARD={int(k):tuple(v) for k,v in _cards['CARD'].items()}` 로 읽어 화면에 두 줄짜리 카드로 그린다(`bake_lines.mjs`/`save_prompts` 계열이 만든다).
한자 편은 `["漢字", "한글음"]` 을 쓰지만, **형식 자체는 한자 전용이 아니다** — 다른 주제는 그 자리에 아무 두 낱말 키워드 쌍(예: `["원인", "결과"]`, `["Before", "After"]`)을 넣으면 된다.
`HILITE`(그 줄 자막에서 금색으로 강조할 낱말) · `SPAN`(카드를 몇 줄 더 유지할지) · `SIDE`(心/力 처럼 좌우 배치) 도 같은 파일에 있다 — SIDE 는 한자 부수 놀이용이라 다른 주제는 대개 안 쓴다.

### QA 게이트가 잡는 것 (`qa_gate.py` · `cutplan_check.py`)

- 어둡고 무서운 낱말(`dark`·`night`·`gloomy`·`ominous` 등) 금지 — 밝은 톤만.
- 장면 프롬프트 안에 글자를 그리게 하면 안 된다(`sign reading`·`text saying` 등) — 한자판·자막은 오버레이 몫이지 장면 안 글자가 아니다.
- 사람이 나오는 컷은 **반드시 `kit.config.json` 의 `characters` 문구를 그대로** 쓴다 — 임의 서술 금지, 안 그러면 컷마다 딴 사람이 나온다.
- 헤드라인(썸네일) ≤14자, 2줄까지.
- 카드 줄 형식은 위 「A. B 에 C. 뜻.」 패턴을 지킨다 — 검사기가 문장 수·재사용 실존 여부·스타일 꼬리 일치까지 자동으로 본다.

## 1. 대본 → 더빙

대본 정본은 `data/longform/<key>.json` 의 `script_v2.lines` (원고 세션이 `qa_gate.py pre <key>` PASS 상태로 넘긴다).

```bash
export ESBUILD=$PWD/node_modules/@esbuild/darwin-arm64/bin/esbuild   # mac (Apple Silicon). Windows 는 node_modules/@esbuild/win32-x64/esbuild.exe
mkdir -p scratch/flow_<key>/_old_wav && mv scratch/flow_<key>/n*.wav scratch/flow_<key>/_old_wav/ 2>/dev/null
node scripts/bake_lines.mjs <key>        # Typecast → scratch/flow_<key>/n01.wav … + lines.json
```
로그 마지막 줄 `<key>: N문장` 이 대본 줄 수와 같아야 한다.

## 2. 컷 계획 (사람이 쓰는 유일한 창작 단계)

`scripts/top10_plan.py` 의 `PLANS['<key>'] = dict(new=…, map=…, thumb=TH(…))` 블록을 `def build` 앞에 추가한다. 기존 블록(예: `fire_water`, `person_life`)을 그대로 본뜬다.

- `new`: 컷 10~12개. 사람 나오는 컷은 `scene(f"{C2} … {MP} …")`, 사물만은 `diagram("…")`. **사람은 반드시 상수만**({C2} 아이·{MP} 엄마·{DP} 아빠·{F2} 친구·{TEACH} 선생님·{GRM} 할머니) — 다른 말로 사람을 쓰면 `cutplan_check` 가 떨어뜨린다(편마다 캐릭터가 달라짐).
- `map`: 대본 줄 번호 1..N 전부에 컷 키. 「같이 볼까요?」·「…라고 풀어요」 줄은 글자 뜻을 보여 주는 `diagram` 컷.
- 금지어: dark·night 등 어두운 톤, 사물 위 글자/로고/「word tiles」.
- `thumb=TH(a_flow, a_head, panel, b_flow, b_head, doc, c_flow, c_bg, c_head)`: a=아이 미디엄샷(오른쪽), b=엄마+문서카드(`{LT}`), c=단색 배경 얼굴 클로즈업. 헤드라인 2줄 합쳐 14자 이하, 펀치라인 폰트 ≥120.

```bash
python3 scripts/top10_plan.py <key>       # → data/longform/prompts/<key>.json
python3 scripts/cutplan_check.py <key>         # 8.0 이상 통과할 때까지 ✗ 항목 고친다
```

## 3. Flow 생성 (Aside)

Flow 는 공개 API 가 없어 브라우저 UI 를 자동화한다. Aside 에 Google 로그인된 Flow 탭이 하나 있어야 한다(`aside repl 'console.log(JSON.stringify(await listBrowserTabs()))'` 로 id 확인 → `FLOW_TAB`).

```bash
python3 scripts/aside_flow_submit.py <key>            # 새 프로젝트 + 영상 컷 전부 제출 (URL 출력·flow_projects.txt 기록)
python3 scripts/aside_flow_submit.py <key> --thumbs   # 썸네일 3장 이미지 모드로 제출 후 영상 모드 복귀
```
- 여러 편이면 영상 제출을 전부 먼저, 썸네일은 뒤에 몰아서(모드 설정이 계정 공통).
- 한 번에 24장 이상 몰아 넣으면 「unusual activity — Failed」가 몇 개 뜬다(과금 없음) → 1분 뒤 타일의 Retry.
- **Aside 는 영속 Flow 탭이 하나뿐**이다. 두 편을 동시에 돌리지 말고 순서대로.

## 4. 다운로드·배치

```bash
python3 scripts/aside_flow_dl.py <project_url> <outdir>     # 영상 720p / 이미지 1K, 파일명 = Flow 자동 캡션
```
캡션을 프롬프트 문구와 대조해 `assets/flow/<key>/<컷키>.mp4`, 썸네일은 `assets/flow/<key>/thumb/{a,b,c}.jpg` 로 옮긴다. 헷갈리면 `ffmpeg -ss 2 -i 파일 -frames:v 1 x.png` 로 한 프레임 본다.
- 개수 = `new_prompts` 키 수여야 한다. Flow 가 조용히 빼먹는 컷(10개 중 1개꼴)은 그 프롬프트만 같은 프로젝트에 다시 제출.
- 같은 편 안에서 MD5 가 같은 파일이 있으면 잘못 받은 것.
- 사물에 가짜 글자가 새겨졌으면 크롭: `ffmpeg -i in.mp4 -vf "crop=iw*0.68:ih*0.68:(iw-iw*0.68)/2:ih-ih*0.68,scale=1280:720" -c:v libx264 -crf 16 -pix_fmt yuv420p -an out.mp4`

## 5. 썸네일·조립·검사

```bash
python3 scripts/make_thumb.py <key>                 # final-a/b/c.png, 셋 다 「썸네일 검사 PASS」
python3 scripts/flow_assemble.py <key> --deploy     # 롱폼 → remotion/out/<key>_deploy.mp4 (5~10분)
python3 scripts/flow_assemble.py <key> --short      # 세로 쇼츠 → scratch/flow_<key>/<key>_short.mp4
python3 scripts/qa_gate.py post <key>               # 8.0 이상
python3 scripts/sheet.py <key>                 # 12프레임 시트 → 눈으로 한 번: 글자·어두움·카드가 얼굴 가림·캐릭터 이탈
```

## 6. R2 · 유튜브

```bash
# macOS(zsh 있음)
zsh scripts/prep_more.sh <key>     # R2 에 video/short/thumb_a 업로드 + 업로드 메타(yt_meta.json)
echo "<key> long allirang"  >> $FLOW_WORK/aside_queue.txt     # 큐: <key> <long|short> <allirang|daechung>
echo "<key> short allirang" >> $FLOW_WORK/aside_queue.txt
echo "<key> long daechung"  >> $FLOW_WORK/aside_queue.txt
echo "<key> short daechung" >> $FLOW_WORK/aside_queue.txt
zsh scripts/drain_uploads.sh &     # Aside 로 Studio 업로드(제목·설명·태그·재생목록·AI 아니오·공개), 편 JSON 에 ID 기록

# Windows(또는 sed/zsh 없이 어디서나) — 같은 일을 하는 파이썬 판
python3 scripts/prep_more.py <key>
"<key> long allirang" | Out-File -Append -Encoding utf8 $env:FLOW_WORK\aside_queue.txt
python3 scripts/drain_uploads.py     # 백그라운드로 돌리려면 Start-Process 나 별 터미널 탭
```
- 채널: 환경변수 `YT_CHANNELS='{"allirang": ["<aside Studio 탭 id>", "<채널 ID UC…>", "<재생목록 이름>"], "daechung": [...]}'` 로 준다. Aside 에 각 채널 Studio 탭이 열려 있어야 한다.
- 채널당 **하루 업로드 한도**가 있다(≈20~25건). 걸리면 다이얼로그가 「Video link — Creating link…」에서 멈춘다 → 드레이너가 그 채널을 건너뛰고 나머지를 큐 파일에 남긴다. 다음 날 다시 돌린다.
- **구글 드라이브 재사용 라이브러리**: `prep_more.sh` 가 끝에 `python3 scripts/drive_backup_clips.py <key>` 를 백그라운드로 띄운다 → `My Drive/allirang-library/`(01 Flow 원본 · 02 자막없는 · 03 배포본 · 04 썸네일 · 05 음성 + INDEX.csv/EPISODES.csv). Google Drive 데스크톱 앱이 켜져 있어야 실제로 올라간다(Windows 는 `DRIVE_LIB=G:\My Drive\allirang-library`). 자막없는 판(02)이 필요하면 조립 때 `flow_assemble.py <key> --clean` 을 한 번 더.
- 편 JSON: `status: published`, `video: https://media.brainhz.life/allirang/<key>/video.mp4` 로 바꾼 뒤 `npm run build && vercel deploy --prod --yes`.

## 7. 규칙 요약(어기면 반려)

- 소리는 WAV 원음, 오디오 element 하나(`.claude/rules.md`)
- 앱·영상 안에 「공부·학습·훈련」 금지 → 「오늘의 말」
- 어원 라벨은 각주, 이야기가 먼저
- 어두운 이미지 금지, 사물 위 글자 금지
- 배포 전 실제 프레임 시트로 자체 리뷰(`sheet.py`) — 오쌤은 완성 영상만 본다

## 8. Aside 가 없을 때 — Playwright 폴백

`aside_flow_submit.py`·`aside_flow_dl.py`·`aside_up.py` 는 브라우저를 직접 부르지 않는다 — 전부 `scripts/browser.py` 의 `repl(js)` 를 거친다.
`browser.py` 는 PATH 에 `aside` 가 있으면 `aside repl '<JS>'` 로 그대로 넘기고(1순위, 0절), 없으면 `node scripts/pw_runner.mjs` 를 스폰해 Playwright 로 같은 JS 환경(`attachBrowserTab(id)`, `openTab(url)`, `listBrowserTabs()`, `sleep(ms)`, `fs`)을 흉내 낸다 — 기존 JS 스니펫이 거의 그대로 돈다.

Playwright 러너를 처음 쓸 때:
1. `npm install && npx playwright install chromium`
2. `python3 scripts/browser.py 'console.log(JSON.stringify(await listBrowserTabs()))'` 를 한 번 돌리면 Chromium 창이 뜬다 — 그 창에서 Google(Flow, YouTube Studio)에 수동 로그인해 둔다.
3. 로그인 세션은 `FLOW_WORK/pw-profile`(영속 프로필)에 저장되어 다음 실행부터 재사용된다. `FLOW_TAB`/`YT_CHANNELS` 의 탭 id는 Playwright 경로에서는 URL 부분 문자열이나 숫자 인덱스로 줘도 된다(`pw_runner.mjs`의 `attachBrowserTab` 참고).

Chrome 확장(Claude in Chrome)으로도 같은 JS 를 `javascript_tool` 로 넣어 쓸 수 있다 — 단 한 호출에 컷 4개까지(45초 타임아웃).

## 9. 토큰(클로드 크레딧) 아끼는 법 — 2026-09-25 하루에 배운 것

주간 한도를 가장 많이 깎은 건 **브라우저 왕복과 이미지 리뷰**였다. 편당 순서를 이렇게 잡으면 Fable 기준 편당 ~5천 토큰 이하로 떨어진다.

1. **기계적인 단계는 Sonnet 서브에이전트에** — 더빙·Flow 제출·다운로드·캡션→컷키 매칭·조립·QA·R2·큐 적재(1~7절 전부). Fable(또는 상위 모델)은 컷 계획 작성과 최종 시트 판정만. 에이전트 프롬프트에는 "긴 대기는 `until … ; do sleep 30; done` 한 번의 Bash(타임아웃 600000)로, 결과를 지어내지 말 것"을 꼭 넣는다 — 안 그러면 "너무 길다"며 1단계에서 멈춘다.
2. **폴링하지 않는다** — 30초마다 확인하지 말고 `until [ -f 플래그 ]` 로 막아 두거나 백그라운드 완료 알림만 받는다. 알림이 "interim" 이면 답만 한 줄 하고 아무 것도 하지 않는다.
3. **스크린샷 대신 텍스트** — Flow 타일 수·Failed 수·캡션 목록은 JS 로 읽는다. 시트 리뷰는 편당 **한 장**(12프레임 격자, 1400px 이하로 축소)만 본다. 썸네일 3장도 한 장에 이어 붙여 본다.
4. **프롬프트를 브라우저에 붙여 넣지 않는다** — `aside_flow_submit.py` 는 파일에서 읽어 넘기므로 대화에 프롬프트 본문이 안 실린다. Chrome 확장으로 넣을 땐 공용 상수(캐릭터·TAIL)를 `«CH»` 같은 자리표로 줄이고 페이지 안에서 치환(`__D`).
5. **한 번에 여러 편** — 제출은 9편을 연달아(영상 먼저, 썸네일은 뒤에 묶어서), 다운로드도 프로젝트 단위로 스크립트 한 번. 편 하나씩 대화로 오가면 편당 왕복이 10배다.
6. **업로드는 큐 + 드레이너** — 편이 끝날 때마다 올리지 말고 큐 파일에 4줄 적고 드레이너가 순서대로 비우게 둔다. 채널 한도에 걸린 건 자동으로 다음 날로 넘어간다.
7. **훅 끄기** — 기다리는 동안 Stop 훅이 자꾸 깨우면 토큰만 쓴다. `touch .claude/handoff-off`, 다시 돌릴 때 지운다.
8. **재작업 방지가 최고의 절약** — 캐릭터 상수·금지어·헤드라인 길이를 `cutplan_check` 로 먼저 잡고 Flow 에 보낸다(컷 하나 10크레딧 + 재다운로드 왕복). 가짜 글자는 재생성 대신 크롭(4절).
