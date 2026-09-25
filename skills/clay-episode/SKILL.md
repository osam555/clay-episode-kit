---
name: clay-episode
description: 어떤 주제든(과학·역사·생활·영어·한자…) 클레이 애니 롱폼 2~3분 + 세로 쇼츠 45초 + 썸네일 3종을 대본→더빙→컷 계획→Flow 생성→조립→검사→업로드까지 반자동으로 만드는 절차. 처음 하는 사람용. Windows/macOS.
---

# 클레이 애니 편(episode) 만들기 — 처음 하는 사람을 위한 안내

## 이 문서를 읽는 법

- 처음이면 **0절(설치) → A절(내 프로젝트 만들기) → B절(첫 편 30분 따라 하기)** 순서로만 보세요. 나머지 절은 B절을 한 번 끝낸 뒤에 필요할 때 찾아봅니다.
- `<key>` 는 편 하나의 영문 이름입니다(예 `rainbow`). 파일·폴더 이름에 그대로 쓰이므로 소문자·밑줄만.
- 명령은 프로젝트 폴더(이 저장소를 클론한 곳)에서 칩니다. Windows 는 PowerShell 기준, macOS 는 zsh 기준으로 둘 다 적었습니다.

### 한 편의 결과물과 비용

| 결과물 | 내용 |
|---|---|
| 롱폼 | 16:9, 2~3분(인트로 6초 + 본편 + 엔딩 7초), 자막·키워드 카드 오버레이 |
| 쇼츠 | 9:16, 45초(첫 장면), 위에 훅 제목띠·로고 |
| 썸네일 | a(아이 얼굴+키워드판) · b(어른+문서카드) · c(얼굴 클로즈업, 단색 배경) |

비용: Google Flow 크레딧 **편당 110~130**(6초 영상 컷 10~12개 × 10, 썸네일 이미지는 무료). 사람 손 ≈20분, 기계 대기 ≈30분.

### 용어 5개

| 말 | 뜻 |
|---|---|
| **컷** | Flow 가 만드는 6초짜리 영상 조각. 한 편에 10~12개. 대본 여러 줄이 컷 하나를 나눠 씁니다 |
| **컷 계획** | 대본 줄마다 어떤 컷을 보여 줄지 + 각 컷의 영어 프롬프트. `top10_plan.py` 에 파이썬 딕셔너리로 씁니다 |
| **카드** | 화면 위에 뜨는 두 줄짜리 키워드 패널(예 「굴절 / 빛이 휘어져요」). 한자 편이면 「漢字 / 훈음」 |
| **QA 게이트** | 자동 검사. 컷 계획(`cutplan_check`)과 완성 영상(`qa_gate`) 둘 다 8.0점 이상이어야 다음 단계로 |
| **큐·드레이너** | 업로드할 편을 텍스트 파일에 적어 두면(큐) 스크립트가 순서대로 유튜브에 올리는(드레이너) 방식 |

---

## 0. 설치 (한 번만)

| 것 | Windows | macOS |
|---|---|---|
| Python 3.12+ | python.org 설치, **"Add python.exe to PATH" 체크** | `brew install python` |
| 파이썬 패키지 | `pip install -r requirements.txt` | 동일 |
| Node 20+ | nodejs.org → `npm install` | `brew install node` → `npm install` |
| ffmpeg | gyan.dev 에서 받아 `bin\` 을 PATH 에 추가 (`ffmpeg -version` 으로 확인) | `brew install ffmpeg` |
| **Aside** (브라우저 자동화) | https://aside.com/download → 설치 → `aside login` | 동일 |
| Typecast (더빙 목소리) | typecast.ai 가입 → API 키 → 프로젝트 폴더에 `.env.local` 파일 만들고 `TYPECAST_API_KEY=키` 한 줄. **이 파일은 절대 공유·커밋 금지** | 동일 |
| Cloudflare R2 (영상 임시 저장소, 무료 티어면 충분) | `npx wrangler login`, 버킷 하나 만들고 공개 URL 켜기 | 동일 |
| Google Drive 앱 (선택, 재사용 라이브러리 백업) | 설치·로그인 후 `$env:DRIVE_LIB="G:\My Drive\clay-library"` | `export DRIVE_LIB=~/…/My Drive/clay-library` |

Windows 에서 `.sh` 는 쓰지 않습니다 — 같은 이름의 `.py` 를 씁니다(`prep_more.py`, `drain_uploads.py`).

### Aside 준비 (Flow 와 YouTube Studio 를 이 브라우저로 조작합니다)

1. Aside 앱을 열고 탭을 엽니다: `https://flow.google.com` (Google 로그인, Flow 유료 플랜이어야 Veo 영상이 나옵니다) 와 `https://studio.youtube.com` (업로드할 채널마다 탭 하나).
2. 터미널에서 탭 id 를 읽습니다:
   ```bash
   aside repl 'console.log(JSON.stringify((await listBrowserTabs()).map(t=>[t.targetId,t.url])))'
   ```
3. Flow 탭 id 를 환경변수로 둡니다 — PowerShell `$env:FLOW_TAB="탭id"`, zsh `export FLOW_TAB=탭id`. Studio 탭 id 는 A절의 `kit.config.json` → `channels` 에 적습니다.

Aside 를 못 쓰는 환경이면 8절(Playwright 폴백)로 갑니다.

---

## A. 내 프로젝트 만들기 (주제·캐릭터·브랜드)

```bash
python3 scripts/new_project.py            # 질문에 답하면 kit.config.json 과 폴더가 생깁니다
python3 scripts/new_project.py --defaults # 일단 자리표시자로 만들고 나중에 고칠 때
```

만들어진 `kit.config.json` 에서 **꼭 손볼 세 칸**:

1. **`characters`** — 등장인물의 생김새를 영어 한 줄로 고정합니다. 이 문구가 모든 컷 프롬프트에 그대로 들어가서 편마다 같은 인물이 나옵니다.
   역할 키: `C2`(아이) `MP`(엄마) `DP`(아빠) `F2`(친구) `GRM`(할머니) `TEACH`(선생님). 예:
   `"C2": "a round clay child with a simple round face, rosy cheeks, wearing a yellow raincoat, a small girl with light peach skin and two short black pigtails,"`
   요령: 옷 색·머리 모양·피부색을 꼭 넣고, 다른 인물과 겹치지 않게. 한 번 정하면 바꾸지 마세요.
2. **`brand`** — 이름, 워드마크 PNG, 인트로/엔딩 MP4(없으면 마법사가 임시로 만든 것을 씁니다), 사이트 URL, 해시태그, 설명 꼬리줄.
3. **`channels`** — 유튜브 채널 ID(UC…)·재생목록·Aside 의 Studio 탭 id. 채널이 하나면 `main` 하나만.

`style.tail` 은 그림체입니다. 기본은 파스텔 클레이. 바꾸고 싶으면 이 한 문장만 바꾸면 전 컷에 적용됩니다.
`topic.kind` 는 `generic`(기본) 그대로 둡니다. 한자 어원 편을 만들 때만 `hanja`.

---

## B. 첫 편 30분 따라 하기 — 「무지개는 왜 생길까」

예시 파일 `examples/generic_episode.json` 이 완성된 대본입니다. 이걸 그대로 한 편 뽑아 보면 전 과정이 손에 익습니다.

```bash
# B-1 편 만들기
copy examples\generic_episode.json data\longform\rainbow.json        # Windows
cp   examples/generic_episode.json data/longform/rainbow.json        # macOS

# B-2 작업 파일 뽑기 + 더빙 (Typecast, 1분)
python3 scripts/prepare_lines.py rainbow     # 대본 → scratch/flow_rainbow/lines.json · cards.json
node scripts/bake_lines.mjs rainbow
#   → scratch/flow_rainbow/n01.wav … 와 lines.json. 마지막 줄 "rainbow: 24문장" 이 대본 줄 수와 같아야 정상

# B-3 컷 계획 검사 (예시 계획이 top10_plan.py 에 이미 들어 있습니다)
python3 scripts/top10_plan.py rainbow            # → data/longform/prompts/rainbow.json
python3 scripts/cutplan_check.py rainbow         # "10.0점 통과" 가 나와야 다음으로

# B-4 Flow 에 보내기 (크레딧 ~110 소모)
python3 scripts/aside_flow_submit.py rainbow             # 영상 컷 11개 제출, 프로젝트 URL 출력
python3 scripts/aside_flow_submit.py rainbow --thumbs    # 썸네일 이미지 3장 제출
#   5분 기다립니다 (Aside 창에서 타일이 차오르는 게 보입니다)

# B-5 받기·정리
python3 scripts/aside_flow_dl.py <영상 프로젝트 URL> scratch/dl_rainbow
python3 scripts/aside_flow_dl.py <썸네일 프로젝트 URL> scratch/dl_rainbow_thumbs
#   받은 파일 이름은 Flow 가 붙인 영어 캡션입니다. 4절대로 컷 키 이름으로 바꿔 assets/flow/rainbow/ 에 넣습니다

# B-6 조립·검사
python3 scripts/make_thumb.py rainbow                   # 썸네일 3장, 셋 다 "썸네일 검사 PASS"
python3 scripts/flow_assemble.py rainbow --deploy       # 롱폼 (5~10분)
python3 scripts/flow_assemble.py rainbow --short        # 쇼츠
python3 scripts/qa_gate.py post rainbow                 # 8.0 이상
python3 scripts/sheet.py rainbow                        # 12장면 시트 한 장 — 눈으로 확인

# B-7 올리기
python3 scripts/prep_more.py rainbow                    # R2 에 올리고 제목·설명 메타 생성
#   큐 파일에 "rainbow long main" / "rainbow short main" 두 줄 추가 후
python3 scripts/drain_uploads.py                        # Aside 가 Studio 에서 제목·설명·태그·재생목록·공개까지
```

결과: `remotion/out/rainbow_deploy.mp4`, `scratch/flow_rainbow/rainbow_short.mp4`, `assets/longform/rainbow/thumb/final-a.png` 등, 유튜브에 2개.

---

## 1. 대본 쓰기

`python3 scripts/new_episode.py <key> --word "<주제어>"` 로 뼈대를 만들고 `data/longform/<key>.json` 의 `script_v2.lines` 를 채웁니다.

### 잘 먹힌 구조 (23~28줄, 읽으면 2분~2분 30초)

| 순서 | 줄 수 | 내용 | 예(무지개) |
|---|---|---|---|
| 1 훅 | 1 | 아이의 엉뚱하거나 절실한 질문 | 「비 그친 다음에 왜 무지개가 떠요?」 |
| 2 반응 | 2 | 어른 한 줄, 친구 한 줄 — 살짝 틀린 추측이면 더 좋음 | 「일곱 색깔이 다 있었어!」 |
| 3 전환 | 1 | 「같이 볼까요?」 (나레이터) | |
| 4 핵심 | 1~2 | 원리 한 문장 | 「빛 속에 색이 숨어 있어요」 |
| 5 키워드 | 3~6 | 키워드 하나에 한 줄 「키워드. 한 줄 뜻.」 + 사이사이 아이·친구 리액션 | 「굴절. 빛이 물방울에서 휘어져요.」 |
| 6 반전 | 1~2 | 흔한 오해 바로잡기 / 조심할 점 | 「무지개는 만질 수 없어요, 자리마다 다르게 보여요」 |
| 7 복습 | 2 | 키워드 나열 「A, B, C. 다 ○○.」 | |
| 8 콜백 | 1 | 1번 질문에 대한 아이의 한 줄 답 | 「이제 비 오면 해 반대쪽을 볼래요!」 |

규칙:
- 줄 앞에 화자 태그 `[[child]]` `[[adult]]` `[[friend]]` (목소리 선택용, 자막에는 안 나감). 태그 없는 줄은 나레이터.
- 한 줄 = 한 문장~두 문장, 7초 이내. 어려운 말은 바로 다음 줄에서 아이 말로 풀어 줍니다.
- 밝고 안전하게: 무섭거나 어두운 묘사, 의료·성적·등급 약속 없음.
- 5번 키워드 줄에는 카드를 답니다: `script_v2.cards` 에 `{"line": 줄번호, "title": "굴절", "subtitle": "빛이 휘어져요"}`. 한자 편은 `title` 에 한자, `subtitle` 에 훈음.

JSON 한 줄 형식: `{"ch": 0, "i": 7, "text": "굴절. 빛이 물방울에서 휘어져요.", "g": 7}` (`i`=`g`=줄 번호).

### 더빙

```powershell
python3 scripts/prepare_lines.py <key>                            # 대본(script_v2)·카드를 작업 파일로 (더빙·검사가 읽음)
$env:ESBUILD="$PWD\node_modules\@esbuild\win32-x64\esbuild.exe"   # Windows (macOS Apple Silicon: node_modules/@esbuild/darwin-arm64/bin/esbuild)
node scripts/bake_lines.mjs <key>
```
다시 굽기 전에는 `scratch/flow_<key>/` 의 옛 `n*.wav` 를 `_old_wav/` 로 옮겨 두세요(번호가 섞이면 자막과 소리가 어긋납니다).

---

## 2. 컷 계획 쓰기 (사람이 하는 유일한 창작 단계)

`scripts/top10_plan.py` 에 `PLANS['<key>'] = dict(new={...}, map={...}, thumb=TH(...))` 블록을 `def build` 바로 위에 추가합니다. 예시 블록(`PLANS['rainbow']`, 일반 주제)을 복사해서 고치는 게 가장 빠릅니다.

- **`new`** — 컷 10~12개. `'Nrb_ask': scene(f"{C2} … asking {MP} …")` 처럼 사람 나오는 컷은 `scene()`, 사물만 보이는 컷은 `diagram()`.
  - 사람은 **반드시 `{C2}` `{MP}` `{DP}` `{F2}` `{GRM}` `{TEACH}` 로만** 씁니다. "a boy", "children" 같이 직접 쓰면 검사에서 떨어지고, 통과해도 컷마다 다른 사람이 나옵니다.
  - 한 컷 = 한 동작 + 한 장소. 카메라는 "gentle slow push in" 정도. 6초에 다 보여야 합니다.
  - 금지: 어두운 말(dark, night, scary…), 사물 위 글자·로고·간판(Flow 가 가짜 글자를 그립니다), 사람 수 애매한 표현(many children).
- **`map`** — 대본 줄 번호 1..N 전부에 컷 키. 이웃한 줄이 같은 컷을 써도 됩니다. 「같이 볼까요?」·핵심 원리 줄은 `diagram` 컷이 어울립니다.
- **`thumb=TH(a_flow, a_head, panel, b_flow, b_head, doc, c_flow, c_bg, c_head)`**
  - a: 아이 미디엄샷(오른쪽에 배치) / b: 어른이 문서·물건을 든 모습(`{LT}` 로 왼쪽 배치) / c: 얼굴 클로즈업, `c_bg` 는 `"bright sunny yellow"` 같은 단색.
  - 헤드라인은 두 줄 `[['무지개가', 88, 'WHT'], ['왜 떠요?', 150, 'BOX']]` — 합쳐 **14자 이하**, 둘째 줄(빨간 박스) 폰트 **120 이상**.
  - `panel` 은 `['무지개', '빛의 비밀', 'right']` (키워드 두 줄). `doc` 은 `{'title':'과학 숙제','rows':[3줄],'hl':강조줄}`.

```bash
python3 scripts/top10_plan.py <key>        # 프롬프트 JSON 생성
python3 scripts/cutplan_check.py <key>     # ✗ 가 있으면 고치고 다시. 8.0 이상이어야 Flow 로
```

---

## 3. Flow 생성

```bash
python3 scripts/aside_flow_submit.py <key>            # 새 Flow 프로젝트 + 영상 컷 전부 (URL 이 출력되고 scratch/flow_tools/flow_projects.txt 에도 남음)
python3 scripts/aside_flow_submit.py <key> --thumbs   # 썸네일 3장 (이미지 모드로 바꿨다가 영상 모드로 복귀)
```
- 여러 편을 한꺼번에 만들 땐 **영상 제출을 전부 먼저, 썸네일은 뒤에 몰아서**(모드 설정이 계정 전체에 걸립니다).
- Aside 의 Flow 탭은 하나라 **편 두 개를 동시에 돌리지 않습니다**.
- 생성은 3~5분. 타일이 「Failed — unusual activity」로 뜨면 과금 없는 일시 제한이니 1분 뒤 그 타일의 Retry.

---

## 4. 받기·정리

```bash
python3 scripts/aside_flow_dl.py <프로젝트 URL> <받을 폴더>
```
- 파일 이름은 Flow 가 붙인 영어 캡션입니다(예 `Clay_child_pointing_at_rainbow_….mp4`). 프롬프트와 대조해 `assets/flow/<key>/<컷키>.mp4` 로 이름을 바꿔 옮깁니다. 헷갈리면 `ffmpeg -ss 2 -i 파일 -frames:v 1 x.png` 로 한 장 뽑아 봅니다.
- 썸네일은 `assets/flow/<key>/thumb/a.jpg` `b.jpg` `c.jpg`.
- 개수가 프롬프트 수와 같아야 합니다. Flow 가 조용히 빼먹는 컷(10개 중 1개꼴)은 같은 프로젝트에서 그 프롬프트만 다시 제출합니다.
- 사물에 가짜 글자가 새겨진 컷은 재생성 대신 잘라냅니다:
  `ffmpeg -i in.mp4 -vf "crop=iw*0.68:ih*0.68:(iw-iw*0.68)/2:ih-ih*0.68,scale=1280:720" -c:v libx264 -crf 16 -pix_fmt yuv420p -an out.mp4`

---

## 5. 썸네일·조립·검사

```bash
python3 scripts/make_thumb.py <key>                 # final-a/b/c.png — 셋 다 「썸네일 검사 PASS」
python3 scripts/flow_assemble.py <key> --deploy     # 롱폼 (5~10분)
python3 scripts/flow_assemble.py <key> --short      # 세로 쇼츠 45초
python3 scripts/qa_gate.py post <key>               # 8.0 이상
python3 scripts/sheet.py <key>                      # 12장면 시트 한 장을 눈으로: 글자 없나, 어둡지 않나, 카드가 얼굴을 가리나, 인물이 바뀌지 않았나
```

---

## 6. 올리기 (R2 → YouTube → Drive)

```bash
python3 scripts/prep_more.py <key>        # R2 업로드 + 제목·설명·태그(yt_meta.json) + Drive 백업(백그라운드)
```
큐 파일 `scratch/flow_tools/aside_queue.txt` 에 한 줄씩 `<key> <long|short> <채널키>` 를 적고
```bash
python3 scripts/drain_uploads.py          # 순서대로 Studio 업로드. 끝날 때까지 켜 둡니다
```
- 유튜브는 **채널당 하루 업로드 한도**(대략 20~25건)가 있습니다. 걸리면 드레이너가 그 채널을 건너뛰고 남은 줄을 큐에 둡니다 → 다음 날 다시 실행.
- 업로드된 ID 는 편 JSON(`yt`, `hook_short.yt`)에 기록됩니다.
- 사이트가 있으면 편 JSON 의 `status` 를 `published` 로, `video` 를 R2 URL 로 바꿔 배포합니다.

---

## 7. 이럴 땐 (자주 나는 문제)

| 증상 | 원인·처방 |
|---|---|
| `cutplan_check` ✗ "사람이 나오는데 CHARACTERS 문구를 안 썼다" | 프롬프트에 사람을 직접 묘사함 → `{C2}` 등 상수로 바꾸거나 사물만 나오는 `diagram` 으로 |
| ✗ "헤드라인 N자" | 썸네일 두 줄 합쳐 14자 넘음 → 줄임 |
| `make_thumb` "펀치라인 폰트가 작다" | 둘째 줄 글자가 길어 120px 아래로 줄어듦 → 둘째 줄을 4~6자로 |
| `qa_gate` "밀도 … 미달(정지 %)" | 그 시각의 컷이 거의 안 움직임 → `map` 에서 그 줄을 움직임 있는 컷으로 바꾸고 `--deploy` 다시 |
| 받은 파일이 프롬프트 수보다 적음 | Flow 가 빼먹음 → 그 프롬프트만 재제출(4절) |
| 같은 파일이 두 번 받힘 | 캡션이 같은 타일 두 개 → 첫 번째만 쓰고 나머지 삭제 |
| 인물이 컷마다 다름 | `characters` 문구가 짧음 → 옷 색·머리·피부 명시, 한 컷에 두 아이면 각자 따로 묘사 |
| 사물에 글자·로고 | 4절 크롭. 프롬프트에 "no lettering" 이 있어도 간판·책·달력은 자주 생김 → 애초에 "plain blank" 를 붙임 |
| Studio 다이얼로그가 「Creating link…」에서 멈춤 | 그 채널 일일 한도 → 내일 |
| `bake_lines` 가 esbuild 오류 | `ESBUILD` 환경변수에 OS 에 맞는 실행파일 경로(0절 표) |
| Aside 탭 id 오류 "No open browser tab" | Aside 를 다시 열면 id 가 바뀜 → 0절의 명령으로 다시 읽어 `FLOW_TAB`/`channels` 갱신 |

---

## 8. Aside 없이 (Playwright 폴백)

세 스크립트(`aside_flow_submit/aside_flow_dl/aside_up`)는 `scripts/browser.py` 를 거칩니다. PATH 에 `aside` 가 없으면 자동으로 `node scripts/pw_runner.mjs` 로 Chromium 을 띄워 같은 JS 를 돌립니다.
1. `npm install && npx playwright install chromium`
2. `python3 scripts/browser.py 'console.log(1)'` 를 한 번 실행하면 창이 뜹니다 — 그 창에서 Google(Flow, Studio)에 로그인해 두면 `scratch/flow_tools/pw-profile` 에 저장됩니다.
3. 이 경로에서는 탭 id 대신 URL 일부(`flow.google.com`)나 탭 번호를 `FLOW_TAB`/`channels.studio_tab_hint` 에 줘도 됩니다.

---

## 9. 여러 편을 싸게 만드는 요령 (Claude 와 함께 쓸 때)

1. **기계적인 단계는 서브에이전트(Sonnet)에게** — 더빙·제출·다운로드·정리·조립·검사·업로드 큐. 사람(또는 상위 모델)은 대본·컷 계획·최종 시트 확인만.
   에이전트에게는 "긴 대기는 `until … ; do sleep 30; done` 한 번의 명령으로, 결과를 지어내지 말 것"을 꼭 적어 줍니다.
2. **기다릴 땐 폴링하지 말고** 완료 알림만 받습니다. 스크린샷 대신 텍스트(타일 수·캡션 목록)로 확인합니다.
3. **시리즈 단위로** — 9편이면 제출 9번 연달아(영상 먼저, 썸네일 뒤에), 다운로드도 프로젝트 단위로. 편마다 대화로 오가면 비용이 10배.
4. **큐 + 드레이너** — 편이 끝날 때마다 올리지 말고 큐에 적어 두고 한 번에.
5. **재작업이 제일 비쌉니다** — `cutplan_check` 로 먼저 잡고 Flow 에 보냅니다(컷 하나 10크레딧). 가짜 글자는 재생성 말고 크롭.

## 10. 한자 어원 편을 만들 때만 (옵션)

`kit.config.json` 의 `topic.kind` 를 `"hanja"` 로. 카드는 `["漢字","훈음"]`, 대본 4번 자리에 「글자 풀이 — …라고 풀어요」 1~2줄이 들어가고, 썸네일 `panel` 은 `['漢字','한글음','right']`. `examples/sample_episode.json` 이 그 예입니다. 나머지 절차는 같습니다.
