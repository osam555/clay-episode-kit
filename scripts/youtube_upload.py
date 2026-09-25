#!/usr/bin/env python3
"""알리랑 유튜브 업로드 — YouTube Data API v3.

사전 준비 (한 번만):
  1. Google Cloud Console → API 라이브러리 → YouTube Data API v3 활성화
  2. OAuth 동의 화면 → 외부 → 테스트 사용자에 채널 소유자 이메일 추가
  3. 사용자 인증 정보 → OAuth 2.0 클라이언트 ID → 데스크톱 앱
  4. JSON 다운로드 → .env.local 옆에 .youtube_client_secret.json 으로 저장
  5. python3 scripts/youtube_upload.py --auth   ← 브라우저 열려 로그인, 토큰 저장

사용:
  python3 scripts/youtube_upload.py <episode_id>           에피소드 JSON 에서 메타 읽어 업로드
  python3 scripts/youtube_upload.py <episode_id> --dry      업로드 안 하고 메타만 출력
  python3 scripts/youtube_upload.py --auth                  OAuth 토큰 발급/갱신

규칙:
  - 아동용 selfDeclaredMadeForKids = False (오쌤 지시: 유튜브 아동용 「아니요」)
  - 비공개(private)로 올리고, 공개 전환은 오쌤 승인 후 수동
  - 키·토큰은 .env.local 과 같은 수준으로 취급 — 출력·커밋·문서화 금지
"""
import argparse, json, os, sys

ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
SECRET = f'{ROOT}/.youtube_client_secret.json'
# ⚠ allirang 은 소유자 계정이 관리하는 **브랜드 계정 @allirang** 이다(개인 채널이 아니다) — 예시일 뿐, 자기 채널 라벨로 바꿔 쓴다.
# OAuth 동의 화면에서 채널을 고르는 단계가 나오는데, 거기서 브랜드 채널을 고르지 않으면
# 개인 채널(@johnwu571, 표시이름 「seungjong oh (대충영어)」)로 토큰이 난다 — 2026-09-23 에 6편이 그리 갔다.
# expect_url 로 매 업로드 전에 막는다.
CHANNELS = {
    'allirang': {'token': f'{ROOT}/.youtube_token.json',
                 'label': '알리랑 (브랜드계정)',
                 'expect_url': '@allirang'},
    'daechung': {'token': f'{ROOT}/.youtube_token_daechung.json',
                 'label': '대충영어 (seungjong555)',
                 'expect_url': None},
    # 배포용이 아니다 — 2026-09-23 에 여기로 잘못 올라간 6편을 비공개로 내리려고 둔 슬롯.
    # 같은 구글 계정이지만 브랜드(@allirang)가 아니라 개인 채널이다.
    'johnwu571': {'token': f'{ROOT}/.youtube_token_johnwu571.json',
                  'label': '개인 채널 (배포용 아님)',
                  'expect_url': '@johnwu571'},
}
DEFAULT_CHANNEL = 'allirang'
PUBLISH_CHANNELS = ['allirang', 'daechung']   # --both 대상. johnwu571 은 정리용이라 뺀다.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
           'https://www.googleapis.com/auth/youtube']


def get_credentials(channel=DEFAULT_CHANNEL):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    token_path = CHANNELS[channel]['token']

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(SECRET):
                sys.exit(f'OAuth 클라이언트 시크릿 없음: {SECRET}\n'
                         'Google Cloud Console 에서 OAuth 클라이언트 만들어 다운로드하세요.')
            sec = json.load(open(SECRET))
            if 'web' in sec and 'installed' not in sec:
                sec['installed'] = {**sec.pop('web'),
                                    'redirect_uris': ['http://localhost']}
                tmp = SECRET + '.tmp'
                json.dump(sec, open(tmp, 'w'))
                flow = InstalledAppFlow.from_client_secrets_file(tmp, SCOPES)
                os.remove(tmp)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(SECRET, SCOPES)
            # 브랜드 계정은 동의 화면에서 **채널을 골라야** 한다. 구글이 지난 선택(개인 채널)을
            # 기억해 건너뛰면 엉뚱한 채널로 토큰이 난다(2026-09-23, 6편이 개인 채널로 갔다).
            # select_account = 계정 다시 고르기 · consent = 동의를 다시 받아 채널 선택 단계를 띄운다.
            creds = flow.run_local_server(port=0, prompt='select_account consent')
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    return creds


def load_episode_meta(eid):
    ep = json.load(open(f'{ROOT}/data/longform/{eid}.json', encoding='utf-8'))
    title = ep['title_ko']
    desc_lines = [
        ep.get('title_en', ''),
        '',
        ep.get('dictNote', '').split('.')[0] + '.',
        '',
        '📖 알리랑 — 한자 어원으로 배우는 우리말',
        f'🌐 https://allirang.com/word/{eid}',
    ]
    tags = ['한자', '어원', '우리말', '초등국어', '알리랑']
    h = ep.get('master', {}).get('char', {})
    if h.get('h'):
        tags.append(h['h'])
    if h.get('k'):
        tags.append(h['k'])
    for ch in ep.get('chapters', []):
        r = ch.get('roman', '')
        if r and r not in tags:
            tags.append(r)
    # A 세션이 쓴 유튜브 메타(yt_meta)가 있으면 그것이 우선 — 제목 후보 첫 줄·태그·설명 (2026-09-23 gae)
    ym = ep.get('yt_meta') or {}
    if ym.get('titles'):
        title = ym['titles'][0]
    if ym.get('description'):
        desc_lines = [ym['description'], '', '📖 알리랑 — 한자 어원으로 배우는 우리말', f'🌐 https://allirang.com/word/{eid}']
    tags += ym.get('tags', [])
    tags = list(dict.fromkeys(tags))

    video_path = ep.get('_local_video') or f'{ROOT}/remotion/out/{eid.replace("sim_","")}_deploy.mp4'
    for alt in [f'{ROOT}/remotion/out/{eid}_deploy.mp4',
                f'{ROOT}/remotion/out/{eid.replace("sim_","")}_deploy.mp4']:
        if os.path.exists(video_path):
            break
        if os.path.exists(alt):
            video_path = alt

    # 편 id 폴더가 먼저 — 마음 시리즈 v2(sim_love 등)는 옛 폴더(love)에 옛 썸네일이 남아 있다
    thumb_path = f'{ROOT}/assets/longform/{eid}/thumb/final-a.png'
    if not os.path.exists(thumb_path):
        thumb_path = f'{ROOT}/assets/longform/{eid.replace("sim_","")}/thumb/final-a.png'
    if not os.path.exists(thumb_path):
        thumb_path = None

    # dictNote 는 어원 표기에 ASCII "<<"(...에서 왔다) 를 쓴다 — YouTube API 가 설명란의 "<"/">" 를
    # invalidDescription 으로 거부한다(2026-09-24 eorida 겪음). 전각 ＜＞ 는 괜찮으니 ASCII 만 없앤다.
    desc = '\n'.join(desc_lines).replace('<<', '←').replace('<', '').replace('>', '')

    return {
        'eid': eid,
        'title': title,
        'description': desc,
        'tags': tags,
        'video_path': video_path,
        'thumb_path': thumb_path,
        'category': '27',  # Education
    }


def load_part_meta(eid, part):
    """편 JSON 안의 부분 영상(예: hangawi.greeting_short — 세로 인사 쇼츠)을 올릴 메타.
    2026-09-23 한가위 인사 쇼츠. 부분에 title/description 이 있으면 쓰고, 없으면 편 메타로 만든다.
    videoId 는 편 JSON 의 그 부분 안(part.yt / part.yt_daechung)에 적는다 — 롱폼 칸과 섞이지 않게."""
    ep = json.load(open(f'{ROOT}/data/longform/{eid}.json', encoding='utf-8'))
    pt = ep[part]
    title = pt.get('title') or (ep['title_ko'].split(' — ')[0] + ' #Shorts')
    desc = pt.get('description') or '\n'.join([
        ep.get('title_en', ''), '',
        f'📖 전체 영상: https://allirang.com/word/{eid}',
        '알리랑 — 한자 어원으로 배우는 우리말'])
    tags = list(dict.fromkeys(['알리랑', '한자', '어원', '우리말', 'Shorts'] + (ep.get('yt_meta') or {}).get('tags', [])))
    return {'eid': eid, 'part': part, 'title': title, 'description': desc, 'tags': tags,
            'video_path': f"{ROOT}/{pt['render']['deploy']}", 'thumb_path': None, 'category': '27'}


def upload(meta, dry=False, channel=DEFAULT_CHANNEL):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if not os.path.exists(meta['video_path']):
        sys.exit(f"영상 파일 없음: {meta['video_path']}")

    if dry:
        print('=== 업로드 메타 ===')
        print(f"제목: {meta['title']}")
        print(f"설명:\n{meta['description']}")
        print(f"태그: {', '.join(meta['tags'])}")
        print(f"영상: {meta['video_path']}")
        print(f"썸네일: {meta['thumb_path']}")
        print(f"카테고리: {meta['category']} (Education)")
        print(f"공개: public (공개)")
        print(f"아동용: 아니요")
        return

    creds = get_credentials(channel)
    yt = build('youtube', 'v3', credentials=creds)

    # 토큰이 실제로 어느 채널을 가리키는지 찍는다 — label 만 믿으면 안 된다(2026-09-23)
    me = yt.channels().list(part='snippet', mine=True).execute()['items'][0]
    url = me['snippet'].get('customUrl', '—')
    print(f"   → 채널 「{me['snippet']['title']}」 {url}")
    exp = CHANNELS[channel].get('expect_url')
    if exp and url != exp:
        sys.exit(f'⛔ 채널이 다르다 — {exp} 를 기대했는데 {url} 이다.\n'
                 f'   토큰을 다시 받아라: youtube_upload.py --auth --channel {channel}')

    body = {
        'snippet': {
            'title': meta['title'],
            'description': meta['description'],
            'tags': meta['tags'],
            'categoryId': meta['category'],
            'defaultLanguage': 'ko',
            'defaultAudioLanguage': 'ko',
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False,
        },
    }

    media = MediaFileUpload(meta['video_path'], mimetype='video/mp4',
                            resumable=True, chunksize=10*1024*1024)

    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    print(f'업로드 시작: {meta["title"]}')
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f'  {pct}%')

    vid = resp['id']
    print(f'✅ 업로드 완료: https://youtu.be/{vid}')

    if meta['thumb_path'] and os.path.exists(meta['thumb_path']):
        # 갓 올린 영상은 몇 초간 thumbnails.set 이 404(videoNotFound)를 낸다 — 2026-09-24 jigu 재업로드가 여기서 죽어 JSON 기록·두 번째 채널을 놓쳤다
        import time
        for i in range(5):
            try:
                yt.thumbnails().set(videoId=vid,
                                    media_body=MediaFileUpload(meta['thumb_path'],
                                                               mimetype='image/png')).execute()
                print('  썸네일 설정 완료'); break
            except Exception as e:
                if i == 4: print(f'  ⚠ 썸네일 실패(영상은 올라감): {e}'); break
                time.sleep(6)

    # 대충영어 업로드본은 재생목록 「아리랑 알리랑 allirang」에 넣는다(오쌤 2026-09-19) — 2026-09-24 까지 수동이라 22편이 빠져 있었다
    pl = PLAYLIST.get(channel)
    if pl and not meta.get('part'):
        yt.playlistItems().insert(part='snippet', body={'snippet': {
            'playlistId': pl, 'resourceId': {'kind': 'youtube#video', 'videoId': vid}}}).execute()
        print(f'  재생목록 추가: {pl}')

    record_id(meta['eid'], channel, vid, meta.get('part'))
    return vid


# 편 JSON 의 어느 칸에 videoId 를 적는가 — 채널별로 다르다
YT_FIELD = {'allirang': 'yt', 'daechung': 'yt_daechung'}
PLAYLIST = {'daechung': 'PLVkZur3-_ysc'}   # 아리랑 알리랑 allirang


def record_id(eid, channel, vid, part=None):
    """업로드 직후 편 JSON 에 videoId 를 남긴다.
    2026-09-23 사고: --both 가 한쪽에서 실패해 재시도했더니 성공했던 채널에 또 올라갔다.
    기록이 없으면 이미 올린 걸 알 방법이 없어 중복을 못 막는다(sim_calm·sim_parent·simjeong 3건 발생)."""
    p = f'{ROOT}/data/longform/{eid}.json'
    if not os.path.exists(p):
        return
    ep = json.load(open(p, encoding='utf-8'))
    (ep[part] if part else ep)[YT_FIELD[channel]] = vid
    json.dump(ep, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'  편 JSON 기록: {part + "." if part else ""}{YT_FIELD[channel]}={vid}')


def already_uploaded(eid, channel, part=None):
    """이 편(또는 편의 부분 영상)이 이 채널에 이미 올라갔으면 videoId 를 준다."""
    p = f'{ROOT}/data/longform/{eid}.json'
    if not os.path.exists(p):
        return None
    ep = json.load(open(p, encoding='utf-8'))
    return (ep.get(part) or {} if part else ep).get(YT_FIELD[channel])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode', nargs='?')
    ap.add_argument('--auth', action='store_true')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--channel', default=DEFAULT_CHANNEL,
                    choices=list(CHANNELS.keys()),
                    help='업로드 채널 (기본: allirang)')
    ap.add_argument('--both', action='store_true',
                    help='양쪽 채널에 모두 업로드')
    ap.add_argument('--part', help='편 JSON 안의 부분 영상 칸(예: greeting_short) — 세로 쇼츠 등')
    ap.add_argument('--force', action='store_true',
                    help='편 JSON 에 videoId 가 있어도 다시 올린다(중복 주의)')
    a = ap.parse_args()

    if a.auth:
        ch = a.channel
        exp = CHANNELS[ch].get('expect_url')
        print(f'채널: {CHANNELS[ch]["label"]}'
              + (f' — 동의 화면에서 반드시 {exp} 채널을 고를 것(브랜드 계정)' if exp else ''))
        creds = get_credentials(ch)
        from googleapiclient.discovery import build
        me = build('youtube', 'v3', credentials=creds).channels().list(
            part='snippet', mine=True).execute()['items'][0]['snippet']
        url = me.get('customUrl', '—')
        print(f'   토큰이 잡은 채널: 「{me["title"]}」 {url}')
        if exp and url != exp:
            os.remove(CHANNELS[ch]['token'])
            sys.exit(f'⛔ {exp} 가 아니라 {url} 이다 — 토큰을 지웠다.\n'
                     f'   다시 실행해 동의 화면에서 {exp} 채널을 고르세요.')
        print(f'✅ {CHANNELS[ch]["label"]} OAuth 토큰 저장 완료')
        return

    if not a.episode:
        sys.exit('사용법: youtube_upload.py <episode_id> [--dry] [--channel allirang|daechung] [--both]')

    if not a.dry and not a.part:
        # 대본 게이트(qa_gate pre) 통과 + 그 뒤 대본 무변경일 때만 올린다 — 2026-09-23 고아 편이 대본 검사 없이 배포됨
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'longform'))
        import script_source
        script_source.require(a.episode)

    meta = load_part_meta(a.episode, a.part) if a.part else load_episode_meta(a.episode)
    # --both 는 **배포 채널 둘**만이다 — johnwu571 은 정리용 슬롯이라 여기 들어오면 안 된다
    targets = PUBLISH_CHANNELS if a.both else [a.channel]
    for ch in targets:
        print(f'\n=== {CHANNELS[ch]["label"]} ===')
        dup = already_uploaded(a.episode, ch, a.part)
        if dup and not a.dry and not a.force:
            print(f'⏭  건너뜀 — 이미 올라가 있다: https://youtu.be/{dup}')
            print(f'   다시 올리려면 --force (옛 것은 yt_privacy.py 로 비공개 처리할 것)')
            continue
        upload(meta, dry=a.dry, channel=ch)


if __name__ == '__main__':
    main()
