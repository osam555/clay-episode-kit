# clay-episode-kit

한자·어원 교육용 **클레이 애니메이션 롱폼(2~3분) + 세로 쇼츠 45초 + 썸네일 3종**을
대본 → Typecast 더빙 → 컷 계획 → Google Flow(Veo) 생성 → ffmpeg 조립 → 품질 게이트 → R2 → YouTube 까지
반자동으로 만드는 스크립트와 Claude Code 스킬입니다. macOS/Windows.

- `skills/clay-episode/SKILL.md` — 전체 절차(준비물 표, 단계별 명령, 규칙, Aside 없이 Playwright 로 대체하는 법, 토큰 절약법)
- `scripts/` — 컷 계획 생성기(`top10_plan.py`, 예시 1편 포함) · 계획 검사(`cutplan_check.py`) · Flow 제출/다운로드(`aside_flow_*.py`) · 조립 후 검토 시트(`sheet.py`) · R2/메타(`prep_more.sh`) · YouTube Studio 업로드 큐(`aside_up.py`, `drain_uploads.sh`) · Google Drive 재사용 라이브러리(`drive_backup_clips.py`)

이 키트에는 **대본·프롬프트 데이터·조립기(flow_assemble/qa_gate/make_thumb)는 포함되지 않습니다** — 그 부분은 각자 프로젝트의 것을 씁니다. 스크립트가 기대하는 저장소 구조와 환경변수(`ALLIRANG_ROOT`, `FLOW_WORK`, `FLOW_TAB`, `DRIVE_LIB`)는 SKILL.md 0절을 보세요.

주의: Google Flow 는 공개 API 가 없어 브라우저 UI 자동화(Aside/Playwright)를 씁니다. 계정 약관과 크레딧 소모(6초 컷당 10크레딧)를 확인하고 쓰세요.
