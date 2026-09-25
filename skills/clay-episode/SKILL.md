---
name: clay-episode
description: 알리랑 클레이 애니 롱폼 1편(+45초 쇼츠+썸네일 3종)을 대본→더빙→컷 계획→Flow 생성→조립→QA→R2→유튜브까지 만드는 절차. Windows/macOS 공통.
---

# 클레이 애니 편 제작 (2026-09-25 정본)

한 편 = 롱폼 16:9(2~3분, 인트로·엔딩 포함) + 세로 쇼츠 45초(첫 장면, 제목띠·로고) + 썸네일 3종(a/b/c).
소요: 편당 Flow 크레딧 ≈110~130(6초 컷 10~12개 × 10, 썸네일 이미지는 무료), 사람 시간 ≈20분(대기 제외).

## 0. 준비물

| 것 | macOS | Windows |
|---|---|---|
| Python 3.12+, `pip install pillow numpy` | brew | python.org 설치, PATH 등록 |
| Node 20+ (`npm ci`) | brew | nodejs.org |
| ffmpeg/ffprobe | brew install ffmpeg | gyan.dev 빌드 → PATH |
| `.sh` 스크립트 실행 | zsh | **Git Bash** 또는 WSL (PowerShell 불가) |
| Typecast 키 | `.env.local` 의 `TYPECAST_API_KEY` — 절대 출력·커밋 금지 | 동일 |
| Cloudflare R2 | `npx wrangler login` 1회 | 동일 |
| Flow(labs.google/flow) 로그인 브라우저 | **Aside**(`aside` CLI, Playwright 내장) 또는 Claude Chrome 확장 | Aside Windows 빌드가 없으면 Playwright 로 `attachBrowserTab` 부분만 바꿔 쓴다(아래 8절) |
| 유튜브 업로드 | Aside 로 Studio UI 조작(API 쿼터 안 씀) | 동일 |

환경변수(선택): `ALLIRANG_ROOT`(저장소 경로, 기본은 스크립트 위치에서 추정), `FLOW_WORK`(작업 파일 폴더, 기본 `scratch/flow_tools`), `FLOW_TAB`(Aside 의 Flow 탭 id).
스크립트는 전부 `scripts/longform/flow/` 에 있다. Windows 는 `/tmp/...` 경로를 쓰는 곳(큐·로그)에 `FLOW_WORK` 아래 경로를 주면 된다.

## 1. 대본 → 더빙

대본 정본은 `data/longform/<key>.json` 의 `script_v2.lines` (원고 세션이 `qa_gate.py pre <key>` PASS 상태로 넘긴다).

```bash
export ESBUILD=$PWD/node_modules/@esbuild/darwin-arm64/bin/esbuild   # mac (Apple Silicon). Windows 는 node_modules/@esbuild/win32-x64/esbuild.exe
mkdir -p scratch/flow_<key>/_old_wav && mv scratch/flow_<key>/n*.wav scratch/flow_<key>/_old_wav/ 2>/dev/null
node scripts/longform/bake_lines.mjs <key>        # Typecast → scratch/flow_<key>/n01.wav … + lines.json
```
로그 마지막 줄 `<key>: N문장` 이 대본 줄 수와 같아야 한다.

## 2. 컷 계획 (사람이 쓰는 유일한 창작 단계)

`scripts/longform/flow/top10_plan.py` 의 `PLANS['<key>'] = dict(new=…, map=…, thumb=TH(…))` 블록을 `def build` 앞에 추가한다. 기존 블록(예: `fire_water`, `person_life`)을 그대로 본뜬다.

- `new`: 컷 10~12개. 사람 나오는 컷은 `scene(f"{C2} … {MP} …")`, 사물만은 `diagram("…")`. **사람은 반드시 상수만**({C2} 아이·{MP} 엄마·{DP} 아빠·{F2} 친구·{TEACH} 선생님·{GRM} 할머니) — 다른 말로 사람을 쓰면 `cutplan_check` 가 떨어뜨린다(편마다 캐릭터가 달라짐).
- `map`: 대본 줄 번호 1..N 전부에 컷 키. 「같이 볼까요?」·「…라고 풀어요」 줄은 글자 뜻을 보여 주는 `diagram` 컷.
- 금지어: dark·night 등 어두운 톤, 사물 위 글자/로고/「word tiles」.
- `thumb=TH(a_flow, a_head, panel, b_flow, b_head, doc, c_flow, c_bg, c_head)`: a=아이 미디엄샷(오른쪽), b=엄마+문서카드(`{LT}`), c=단색 배경 얼굴 클로즈업. 헤드라인 2줄 합쳐 14자 이하, 펀치라인 폰트 ≥120.

```bash
python3 scripts/longform/flow/top10_plan.py <key>       # → data/longform/prompts/<key>.json
python3 scripts/longform/cutplan_check.py <key>         # 8.0 이상 통과할 때까지 ✗ 항목 고친다
```

## 3. Flow 생성 (Aside)

Flow 는 공개 API 가 없어 브라우저 UI 를 자동화한다. Aside 에 Google 로그인된 Flow 탭이 하나 있어야 한다(`aside repl 'console.log(JSON.stringify(await listBrowserTabs()))'` 로 id 확인 → `FLOW_TAB`).

```bash
python3 scripts/longform/flow/aside_flow_submit.py <key>            # 새 프로젝트 + 영상 컷 전부 제출 (URL 출력·flow_projects.txt 기록)
python3 scripts/longform/flow/aside_flow_submit.py <key> --thumbs   # 썸네일 3장 이미지 모드로 제출 후 영상 모드 복귀
```
- 여러 편이면 영상 제출을 전부 먼저, 썸네일은 뒤에 몰아서(모드 설정이 계정 공통).
- 한 번에 24장 이상 몰아 넣으면 「unusual activity — Failed」가 몇 개 뜬다(과금 없음) → 1분 뒤 타일의 Retry.
- **Aside 는 영속 Flow 탭이 하나뿐**이다. 두 편을 동시에 돌리지 말고 순서대로.

## 4. 다운로드·배치

```bash
python3 scripts/longform/flow/aside_flow_dl.py <project_url> <outdir>     # 영상 720p / 이미지 1K, 파일명 = Flow 자동 캡션
```
캡션을 프롬프트 문구와 대조해 `assets/flow/<key>/<컷키>.mp4`, 썸네일은 `assets/flow/<key>/thumb/{a,b,c}.jpg` 로 옮긴다. 헷갈리면 `ffmpeg -ss 2 -i 파일 -frames:v 1 x.png` 로 한 프레임 본다.
- 개수 = `new_prompts` 키 수여야 한다. Flow 가 조용히 빼먹는 컷(10개 중 1개꼴)은 그 프롬프트만 같은 프로젝트에 다시 제출.
- 같은 편 안에서 MD5 가 같은 파일이 있으면 잘못 받은 것.
- 사물에 가짜 글자가 새겨졌으면 크롭: `ffmpeg -i in.mp4 -vf "crop=iw*0.68:ih*0.68:(iw-iw*0.68)/2:ih-ih*0.68,scale=1280:720" -c:v libx264 -crf 16 -pix_fmt yuv420p -an out.mp4`

## 5. 썸네일·조립·검사

```bash
python3 scripts/longform/make_thumb.py <key>                 # final-a/b/c.png, 셋 다 「썸네일 검사 PASS」
python3 scripts/longform/flow_assemble.py <key> --deploy     # 롱폼 → remotion/out/<key>_deploy.mp4 (5~10분)
python3 scripts/longform/flow_assemble.py <key> --short      # 세로 쇼츠 → scratch/flow_<key>/<key>_short.mp4
python3 scripts/longform/qa_gate.py post <key>               # 8.0 이상
python3 scripts/longform/flow/sheet.py <key>                 # 12프레임 시트 → 눈으로 한 번: 글자·어두움·카드가 얼굴 가림·캐릭터 이탈
```

## 6. R2 · 유튜브

```bash
zsh scripts/longform/flow/prep_more.sh <key>     # R2 에 video/short/thumb_a 업로드 + 업로드 메타(yt_meta.json)
echo "<key> long allirang"  >> $FLOW_WORK/aside_queue.txt     # 큐: <key> <long|short> <allirang|daechung>
echo "<key> short allirang" >> $FLOW_WORK/aside_queue.txt
echo "<key> long daechung"  >> $FLOW_WORK/aside_queue.txt
echo "<key> short daechung" >> $FLOW_WORK/aside_queue.txt
zsh scripts/longform/flow/drain_uploads.sh &     # Aside 로 Studio 업로드(제목·설명·태그·재생목록·AI 아니오·공개), 편 JSON 에 ID 기록
```
- 채널: 환경변수 `YT_CHANNELS='{"allirang": ["<aside Studio 탭 id>", "<채널 ID UC…>", "<재생목록 이름>"], "daechung": [...]}'` 로 준다. Aside 에 각 채널 Studio 탭이 열려 있어야 한다.
- 채널당 **하루 업로드 한도**가 있다(≈20~25건). 걸리면 다이얼로그가 「Video link — Creating link…」에서 멈춘다 → 드레이너가 그 채널을 건너뛰고 나머지를 큐 파일에 남긴다. 다음 날 다시 돌린다.
- **구글 드라이브 재사용 라이브러리**: `prep_more.sh` 가 끝에 `python3 scripts/longform/drive_backup_clips.py <key>` 를 백그라운드로 띄운다 → `My Drive/allirang-library/`(01 Flow 원본 · 02 자막없는 · 03 배포본 · 04 썸네일 · 05 음성 + INDEX.csv/EPISODES.csv). Google Drive 데스크톱 앱이 켜져 있어야 실제로 올라간다(Windows 는 `DRIVE_LIB=G:\My Drive\allirang-library`). 자막없는 판(02)이 필요하면 조립 때 `flow_assemble.py <key> --clean` 을 한 번 더.
- 편 JSON: `status: published`, `video: https://media.brainhz.life/allirang/<key>/video.mp4` 로 바꾼 뒤 `npm run build && vercel deploy --prod --yes`.

## 7. 규칙 요약(어기면 반려)

- 소리는 WAV 원음, 오디오 element 하나(`.claude/rules.md`)
- 앱·영상 안에 「공부·학습·훈련」 금지 → 「오늘의 말」
- 어원 라벨은 각주, 이야기가 먼저
- 어두운 이미지 금지, 사물 위 글자 금지
- 배포 전 실제 프레임 시트로 자체 리뷰(`sheet.py`) — 오쌤은 완성 영상만 본다

## 8. Aside 가 없을 때 (Windows 등)

`aside_flow_submit.py`·`aside_flow_dl.py`·`aside_up.py` 는 전부 `aside repl '<JS>'` 를 부르고, JS 안에서 `attachBrowserTab(id)` 로 Playwright `page` 를 얻는 구조다.
Playwright 를 직접 쓰려면 `npx playwright codegen --save-storage=auth.json flow.google.com` 으로 로그인 상태를 저장한 뒤, 같은 JS 본문을 `page` 에 대해 실행하는 러너 하나만 만들면 나머지는 그대로다(다운로드는 `page.waitForEvent('download')` → `download.path()`).
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
