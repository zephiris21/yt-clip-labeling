# 🎬 YouTube 클립 일괄 생성 시스템

## 📋 프로젝트 개요

YouTube 영상에서 5-7초 길이의 클립을 **일괄 자동 생성**하는 도구입니다. 하나의 CSV 파일로 여러 영상의 클립을 한번에 처리할 수 있으며, 침착맨 영상에서 "재밌는 순간"과 "재미없는 순간"을 분류하여 머신러닝 학습 데이터를 만드는 것이 목적입니다.

## 🗂️ 디렉토리 구조

```
프로젝트 루트/
├── config.yaml                    # 설정 파일 (자동 생성)
├── batch_clips.py                 # 일괄 처리 메인 스크립트
├── utils.py                       # 유틸리티 함수들
├── timestamps.csv                 # 모든 클립 정보가 담긴 통합 파일
├── downloads/                     # 원본 영상 저장소
│   ├── VIDEO_ID_1/               # video_id별 폴더
│   │   ├── VIDEO_ID_1_video.mp4  # 비디오 파일
│   │   └── VIDEO_ID_1_audio.m4a  # 오디오 파일
│   └── VIDEO_ID_2/
│       ├── VIDEO_ID_2_video.mp4
│       └── VIDEO_ID_2_audio.m4a
└── clips/                         # 생성된 클립 저장소
    ├── funny/                     # 재밌는 클립들
    │   ├── video/
    │   │   ├── f_001_safe_title_10.5_16.2.mp4
    │   │   └── f_002_safe_title_45.0_51.5.mp4
    │   ├── audio/
    │   │   ├── f_001_safe_title_10.5_16.2.m4a
    │   │   └── f_002_safe_title_45.0_51.5.m4a
    │   └── merged/ (옵션)
    │       ├── f_001_safe_title_10.5_16.2.mp4
    │       └── f_002_safe_title_45.0_51.5.mp4
    └── normal/                    # 일반 클립들
        ├── video/
        ├── audio/
        └── merged/
```

## ⚙️ 설정 파일 (config.yaml)

첫 실행 시 자동으로 생성되며, 필요에 따라 수정 가능합니다:

```yaml
download:
  base_directory: downloads
  merge_audio_video: false         # 다운로드 시 병합 파일 생성 여부

clips:
  output_directory: clips          # 클립 저장 디렉토리
  min_duration: 5.0               # 최소 클립 길이 (초)
  max_duration: 7.0               # 최대 클립 길이 (초)
  merge_clips: true               # 클립 병합 여부

batch:
  skip_existing_downloads: true    # 기존 다운로드 건너뛰기
  continue_on_error: true         # 오류 시 계속 진행
```

## 🚀 사용법 (간단 3단계)

### 1️⃣ timestamps.csv 파일 생성

프로젝트 루트에 `timestamps.csv` 파일을 만들고 다음 형식으로 입력:

```csv
url,start,end,label
https://www.youtube.com/watch?v=EXAMPLE1,10.5,16.2,funny
https://www.youtube.com/watch?v=EXAMPLE1,45.0,51.5,normal
https://www.youtube.com/watch?v=EXAMPLE2,78.3,84.8,f
https://www.youtube.com/watch?v=EXAMPLE2,120.1,125.6,n
# 주석 행은 #으로 시작
```

### 2️⃣ 일괄 처리 실행

```bash
python batch_clips.py
```

### 3️⃣ 결과 확인

`clips/funny/video/`와 `clips/normal/video/` 폴더에서 생성된 클립 확인

## 📝 timestamps.csv 작성 가이드

### 컬럼 설명:
- **url**: YouTube 영상 URL (전체 URL 또는 짧은 URL 모두 가능)
- **start**: 클립 시작 시간 (초 단위, 소수점 가능)
- **end**: 클립 종료 시간 (초 단위, 소수점 가능)
- **label**: 클립 라벨 (아래 참조)

### 유효한 라벨:
- **재밌는 클립**: `funny`, `f`, `F`
- **일반 클립**: `normal`, `n`, `N`

### 시간 형식:
```csv
# 초 단위 (소수점 가능)
10.5,16.2,funny

# 분:초 형식도 지원
1:30,1:37,normal

# 시:분:초 형식도 지원
1:23:45,1:23:52,funny
```

### 예시:
```csv
url,start,end,label
https://www.youtube.com/watch?v=dQw4w9WgXcQ,10.5,16.2,funny
https://www.youtube.com/watch?v=dQw4w9WgXcQ,45.0,51.5,normal
https://youtu.be/dQw4w9WgXcQ,1:30,1:37,f
https://www.youtube.com/watch?v=other_video,78.3,84.8,n
# 침착맨이 놀라는 순간
https://www.youtube.com/watch?v=another_one,2:15,2:22,funny
```

## 🔄 실행 과정

### 진행 단계:
```
🎬 YouTube 일괄 클립 생성기
==================================================
📋 설정 로드 완료
   클립 길이: 5.0-7.0초
   클립 병합: 활성화

📝 timestamps.csv 파싱 중...
⚠️ 무시된 클립들:
   행 5: 클립 길이 3.2초 (허용: 5.0-7.0초)

📊 총 8개 클립, 3개 영상

==============================
🎥 영상 ID: dQw4w9WgXcQ
📋 클립 개수: 3개
⬇️ 다운로드 시작...
📺 제목: Rick Astley - Never Gonna Give You Up
⏱️  길이: 212초 (3.5분)
📹 비디오 다운로드 중...
🎵 오디오 다운로드 중...
✅ 다운로드 완료!

🎬 'Rick_Astley_Never_Gonna_Give_You_Up' 클립 생성 시작... (3개)
🔄 클립 1/3 처리 중... (10.5-16.2초, funny)
✅ f_001_Rick_Astley_Never_Gonna_Give_You_Up_10.5_16.2 생성 완료
🔄 클립 2/3 처리 중... (45.0-51.5초, normal)
✅ n_001_Rick_Astley_Never_Gonna_Give_You_Up_45.0_51.5 생성 완료
📊 영상 'Rick_Astley_Never_Gonna_Give_You_Up' 완료: 생성 2, 건너뜀 0, 실패 0

==================================================
🎉 일괄 처리 완료!
   영상 다운로드: 3개
   영상 건너뜀: 0개
   클립 생성: 8개
   클립 건너뜀: 1개
   클립 실패: 0개
📁 클립 저장 위치:
   Funny: clips/funny/video
   Normal: clips/normal/video
```

## 📁 클립 파일명 규칙

### 형식:
```
{라벨}_{번호}_{안전한제목}_{시작시간}_{종료시간}.{확장자}
```

### 예시:
- **funny 클립**: `f_001_Rick_Astley_Never_Gonna_Give_You_Up_10.5_16.2.mp4`
- **normal 클립**: `n_001_Rick_Astley_Never_Gonna_Give_You_Up_45.0_51.5.mp4`

### 번호 체계:
- **f_001, f_002, f_003...**: funny 클립 전체 순서
- **n_001, n_002, n_003...**: normal 클립 전체 순서

## 🔍 중복 처리 및 재실행

### 영상 다운로드:
- **기존 다운로드 감지**: 같은 video_id 폴더가 있으면 자동으로 건너뛰기
- **설정 변경**: `config.yaml`에서 `skip_existing_downloads: false`로 설정하면 재다운로드

### 클립 생성:
- **중복 감지**: 같은 제목, 시작/종료 시간(±0.1초)의 클립 자동 감지
- **자동 건너뛰기**: 중복 클립은 메시지와 함께 건너뛰기

### 부분 재실행:
```csv
# 특정 영상만 다시 처리하고 싶을 때
url,start,end,label
https://www.youtube.com/watch?v=SPECIFIC_VIDEO,120.0,127.0,funny
https://www.youtube.com/watch?v=SPECIFIC_VIDEO,200.5,206.8,normal
```

## ⚠️ 주의사항 및 오류 처리

### 1. CSV 파일 관리:
- **UTF-8 인코딩으로 저장** (한글 포함 시)
- **Excel에서 편집 시 CSV 형식으로 저장**
- 편집 중에는 스크립트 실행 금지

### 2. 클립 길이 제한:
- **5-7초 범위를 벗어나면 자동으로 무시**
- 메시지로 어떤 클립이 무시되었는지 확인 가능
- `config.yaml`에서 범위 수정 가능

### 3. 오류 발생 시:
```
⚠️ 무시된 클립들:
   행 3: 잘못된 YouTube URL
   행 7: 클립 길이 3.2초 (허용: 5.0-7.0초)
   행 12: 시작시간이 종료시간보다 큼
```

### 4. ffmpeg 의존성:
- **ffmpeg 설치 필수**
- macOS: `brew install ffmpeg`
- Windows: `winget install ffmpeg`

## 🛠️ 설정 커스터마이징

### 클립 길이 범위 변경:
```yaml
clips:
  min_duration: 3.0    # 최소 3초
  max_duration: 10.0   # 최대 10초
```

### 병합 파일 생성:
```yaml
clips:
  merge_clips: true    # video+audio 병합 파일 생성
```

### 배치 처리 옵션:
```yaml
batch:
  skip_existing_downloads: false   # 항상 재다운로드
  continue_on_error: false        # 오류 시 중단
```

## 🎯 ML 활용 예시

### 데이터 로딩:
```python
import glob
import pandas as pd

# 클립 목록 가져오기
funny_clips = glob.glob('clips/funny/video/*.mp4')
normal_clips = glob.glob('clips/normal/video/*.mp4')

# 데이터프레임 생성
data = []
for clip in funny_clips:
    data.append({'path': clip, 'label': 'funny'})
for clip in normal_clips:
    data.append({'path': clip, 'label': 'normal'})

df = pd.DataFrame(data)
print(f"총 {len(df)}개 클립: funny {len(funny_clips)}개, normal {len(normal_clips)}개")
```

### 균형 잡힌 데이터셋:
- **목표**: funny 100-200개, normal 100-200개
- **현재 상태**: 실행 로그에서 확인 가능

## 🔧 문제 해결

### 1. "timestamps.csv 파일을 찾을 수 없습니다":
```bash
# 해결: 프로젝트 루트에 timestamps.csv 생성
touch timestamps.csv
```

### 2. "ffmpeg not found" 오류:
```bash
# macOS
brew install ffmpeg

# Windows
winget install ffmpeg
```

### 3. 다운로드 실패:
```
❌ 다운로드 실패 - 이 영상의 클립들을 건너뜁니다.
```
- **원인**: 비공개 영상, 지역 제한, 네트워크 오류
- **해결**: URL 확인 후 다른 영상으로 테스트

### 4. 권한 오류:
```bash
# 폴더 권한 확인
chmod 755 .
```

## 📊 성능 및 용량

### 처리 속도:
- **다운로드**: 영상당 1-3분 (네트워크 속도에 따라)
- **클립 생성**: 클립당 5-10초

### 저장 용량:
- **원본 영상**: 1080p 기준 100-500MB/10분
- **클립**: 비디오 5-15MB, 오디오 1-3MB/6초 클립

### 권장 사양:
- **여유 공간**: 10GB 이상
- **RAM**: 4GB 이상
- **ffmpeg 버전**: 4.0 이상

---

**💡 팁**: 
- 첫 실행 시에는 2-3개 클립으로 테스트해보세요
- CSV 파일에 주석을 활용해 클립 설명을 남기세요
- 정기적으로 `clips` 폴더를 백업하세요