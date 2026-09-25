# clay-episode-kit

**어떤 주제로도(과학·역사·일상·영단어… 한자 어원도 그중 하나일 뿐)** 클레이 애니메이션 롱폼(2~3분) + 세로 쇼츠 45초 + 썸네일 3종을
대본 → Typecast 더빙 → 컷 계획 → Google Flow(Veo) 생성 → ffmpeg 조립 → 품질 게이트 → R2 → YouTube 까지
반자동으로 만드는 스크립트와 Claude Code 스킬입니다. macOS/Windows.

이 kit 은 원래 한자·어원 교육 채널 **알리랑**(예시 프로젝트, 아래) 용으로 만들었지만, 지금은 `kit.config.json` 하나로
**자기 주제·캐릭터·브랜드·채널**을 넣어 그대로 씁니다 — 코드를 고칠 필요가 없습니다.

## 빠른 시작 — 내 프로젝트로

```bash
git clone https://github.com/osam555/clay-episode-kit.git
cd clay-episode-kit
pip install -r requirements.txt
npm install
npx playwright install chromium
python3 scripts/new_project.py          # 브랜드·캐릭터를 묻고 kit.config.json + 필요한 폴더를 만든다
python3 scripts/new_episode.py <key> --word "<주제어>"   # 편 하나 시작
```
그다음 `skills/clay-episode/SKILL.md` §A(새 주제·캐릭터로 시작하기)부터 따라간다. §0은 Windows 준비물·Aside 설치.

## 설정 — `kit.config.json`

`scripts/kitconfig.py` 가 이 순서로 합쳐 읽습니다: 코드에 박힌 기본값(=알리랑) ← `kit.config.example.json`(있으면) ← `kit.config.json`(있으면, 최종).
`kit.config.json` 이 아예 없으면 예전 그대로(알리랑) 돕니다 — 값 하나하나가 바이트 단위로 같습니다.

| 칸 | 내용 |
|---|---|
| `topic.kind` | `"generic"`(임의 주제, 기본) · `"hanja"`(한자 어원 — 알리랑) |
| `brand` | 이름·워드마크·로고·인트로/엔딩 영상·사이트 URL·해시태그·설명 꼬리줄 |
| `channels` | 유튜브 채널별 토큰 경로·채널 ID·재생목록(`YT_CHANNELS` 환경변수가 있으면 그게 우선) |
| `style.tail` | 모든 이미지 프롬프트 꼬리에 붙는 그림체 문구 |
| `characters` | 캐릭터 역할(아이/엄마/아빠/친구/할아버지/할머니/선생님)마다 고정 시각 묘사 |
| `tts.voices` | Typecast 보이스 id (편 JSON `tts.voices` 가 우선, 이건 새 편 뼈대의 기본값) |
| `thumbnail` | 헤드라인 폰트·색 |

`kit.config.example.json` 은 처음부터 채워 넣는 참고용 템플릿(자리표시자 값)이고, 이 저장소의 `kit.config.json` 은 예시 프로젝트(알리랑, `topic.kind: "hanja"`)를 그대로 담고 있어 지금 당장 돌려도 예전과 같습니다.

- `skills/clay-episode/SKILL.md` — 전체 절차. **§A가 새 주제로 시작하기**, §0이 Windows 준비물·Aside 설치·저장소 레이아웃, §8이 Aside 없을 때 Playwright 폴백. — 다운로드: https://aside.com/download (macOS·Windows, Windows 정식판 2026-09-14 출시; 무료 플랜으로 `aside repl` 사용 가능)
- `scripts/kitconfig.py` — 설정 로더. `scripts/new_project.py` — 새 프로젝트 마법사. `scripts/new_episode.py` — 새 편 뼈대.
- `scripts/` — 대본→더빙(`bake_lines.mjs`/`bake.mjs`) · 컷 계획(`top10_plan.py`) · 계획 검사(`cutplan_check.py`, `script_source.py`, `hanja_check.py`, `northstar_check.py`) · Flow 제출/다운로드(`aside_flow_submit.py`/`aside_flow_dl.py`) · 조립(`flow_assemble.py`) · 품질 게이트(`qa_gate.py`) · 썸네일(`make_thumb.py`/`thumb_lib.py`) · 검토 시트(`sheet.py`) · R2/메타 업로드(`prep_more.sh`/`prep_more.py`) · YouTube 업로드 큐(`aside_up.py`, `drain_uploads.sh`/`drain_uploads.py`, `youtube_upload.py`, `youtube_privacy.py`, `youtube_thumb.py`, `youtube_ab_mark.py`, `ship_short.py`) · Google Drive 재사용 라이브러리(`drive_backup_clips.py`) · 브라우저 추상화(`browser.py`, `pw_runner.mjs`)
- `assets/brand/` — 로고·워드마크·인트로 영상. `remotion/public/fonts/` — Noto Sans CJK KR(Black/Medium)·Black Han Sans(전부 OFL).
- `data/longform/prompts/CHARACTERS.json` — (예시 프로젝트) 컷 계획이 쓰는 공용 캐릭터 상수 — 새 프로젝트는 `kit.config.json` 의 `characters` 를 쓴다.
- `examples/sample_episode.json` — 한자 편(`topic.kind: "hanja"`) 스키마 예시. `examples/generic_episode.json` — 한자 아닌 일반 주제(과학) 편 예시, 키워드 카드 4장 포함(대사는 전부 지어낸 것, 실제 대본 아님).

이 키트에는 **실제 편 대본·프롬프트 데이터·완성 영상은 포함되지 않습니다** — 각자 프로젝트의 `data/longform/<key>.json` 을 만들어 씁니다.
`brainhz-dsp`(더빙 DSP 정본)는 별도 비공개 저장소라 번들되어 있지 않습니다 — `DSP_SRC` 환경변수로 경로를 주거나 이 저장소와 형제 폴더에 `brainhz-dsp` 를 따로 준비하세요.

## 예시 프로젝트 — 알리랑 (한자 어원)

이 kit 을 처음 만든 프로젝트는 한자·어원 교육 채널 **알리랑**입니다. 그대로 써 보려면:

```powershell
git clone https://github.com/osam555/clay-episode-kit.git
cd clay-episode-kit
pip install -r requirements.txt
npm install
npx playwright install chromium
copy examples\sample_episode.json data\longform\sample_episode.json   # 스키마 참고용
```
`kit.config.json` 이 이미 알리랑 값(`topic.kind: "hanja"`)으로 채워져 있으니 그대로 `skills/clay-episode/SKILL.md` §0부터 따라가면 됩니다.

주의: Google Flow 는 공개 API 가 없어 브라우저 UI 자동화(Aside 우선, 없으면 Playwright)를 씁니다. 계정 약관과 크레딧 소모(6초 컷당 10크레딧)를 확인하고 쓰세요.
YouTube 업로드는 `youtube_upload.py`(Data API v3, OAuth) 또는 `aside_up.py`(Studio UI 자동화, API 쿼터 안 씀) 두 경로가 있습니다 — SKILL.md 6절.
