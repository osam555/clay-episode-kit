# clay-episode-kit

한자·어원 교육용 **클레이 애니메이션 롱폼(2~3분) + 세로 쇼츠 45초 + 썸네일 3종**을
대본 → Typecast 더빙 → 컷 계획 → Google Flow(Veo) 생성 → ffmpeg 조립 → 품질 게이트 → R2 → YouTube 까지
반자동으로 만드는 스크립트와 Claude Code 스킬입니다. macOS/Windows.

- `skills/clay-episode/SKILL.md` — 전체 절차. **0절이 Windows 준비물·Aside 설치·저장소 레이아웃**, 8절이 Aside 없을 때 Playwright 폴백. — 다운로드: https://aside.com/download (macOS·Windows, Windows 정식판 2026-09-14 출시; 무료 플랜으로 `aside repl` 사용 가능)
- `scripts/` — 대본→더빙(`bake_lines.mjs`/`bake.mjs`) · 컷 계획(`top10_plan.py`) · 계획 검사(`cutplan_check.py`, `script_source.py`, `hanja_check.py`, `northstar_check.py`) · Flow 제출/다운로드(`aside_flow_submit.py`/`aside_flow_dl.py`) · 조립(`flow_assemble.py`) · 품질 게이트(`qa_gate.py`) · 썸네일(`make_thumb.py`/`thumb_lib.py`) · 검토 시트(`sheet.py`) · R2/메타 업로드(`prep_more.sh`/`prep_more.py`) · YouTube 업로드 큐(`aside_up.py`, `drain_uploads.sh`/`drain_uploads.py`, `youtube_upload.py`, `youtube_privacy.py`, `youtube_thumb.py`, `youtube_ab_mark.py`, `ship_short.py`) · Google Drive 재사용 라이브러리(`drive_backup_clips.py`) · 브라우저 추상화(`browser.py`, `pw_runner.mjs`)
- `assets/brand/` — 로고·워드마크·인트로 영상. `remotion/public/fonts/` — Noto Sans CJK KR(Black/Medium)·Black Han Sans(전부 OFL).
- `data/longform/prompts/CHARACTERS.json` — 컷 계획이 쓰는 공용 캐릭터 상수.
- `examples/sample_episode.json` — `data/longform/<key>.json` 스키마 예시(대사는 전부 지어낸 것, 실제 대본 아님).

이 키트에는 **실제 편 대본·프롬프트 데이터·완성 영상은 포함되지 않습니다** — 각자 프로젝트의 `data/longform/<key>.json` 을 만들어 씁니다.
`brainhz-dsp`(더빙 DSP 정본)는 별도 비공개 저장소라 번들되어 있지 않습니다 — `DSP_SRC` 환경변수로 경로를 주거나 이 저장소와 형제 폴더에 `brainhz-dsp` 를 따로 준비하세요.

## 빠른 시작 (Windows)

```powershell
git clone https://github.com/osam555/clay-episode-kit.git
cd clay-episode-kit
pip install -r requirements.txt
npm install
npx playwright install chromium
copy examples\sample_episode.json data\longform\sample_episode.json   # 스키마 참고용
```
그다음 `skills/clay-episode/SKILL.md` 0절부터 따라간다.

주의: Google Flow 는 공개 API 가 없어 브라우저 UI 자동화(Aside 우선, 없으면 Playwright)를 씁니다. 계정 약관과 크레딧 소모(6초 컷당 10크레딧)를 확인하고 쓰세요.
YouTube 업로드는 `youtube_upload.py`(Data API v3, OAuth) 또는 `aside_up.py`(Studio UI 자동화, API 쿼터 안 씀) 두 경로가 있습니다 — SKILL.md 6절.
