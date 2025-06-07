# 영상 클립 제작 도구 사용 가이드

이 도구는 YouTube 영상을 다운로드하고 지정된 구간의 클립으로 자동 추출하는 기능을 제공합니다. 주로 스트리머 컨텐츠에서 재미있는 순간이나 중요한 맥락을 모아 효율적으로 관리할 수 있습니다.

## 1. 기본 구성

- **single_processor**: 단일 영상 처리 도구
- **batch_processor**: 여러 영상 일괄 처리 도구
- **clips**: 생성된 클립이 저장되는 폴더
- **downloads**: 다운로드된 원본 영상이 저장되는 폴더

## 2. Batch Processor 사용 방법

### 2.1 필요 환경

- Python 3.7 이상
- ffmpeg (비디오 처리용)
- 필요 라이브러리 (`requirements.txt` 참조)

```bash
# 라이브러리 설치
pip install -r requirements.txt

# ffmpeg가 PATH에 등록되어 있어야 합니다
```

### 2.2 timestamps.csv 파일 구성

배치 처리를 위해서는 `batch_processor` 폴더에 `timestamps.csv` 파일을 생성해야 합니다:

```csv
start,end,label,url
# 본탄아메 먹는법
20,27,f,https://www.youtube.com/shorts/y2D6rFwMAow
7,14,n,https://www.youtube.com/shorts/-VkYuFgHNJ0
35,42,b,https://www.youtube.com/watch?v=anotherExample
```

각 열의 의미:
- **start**: 클립 시작 시간(초)
- **end**: 클립 종료 시간(초)
- **label**: 클립 분류 (f/n/b 또는 funny/normal/boring)
- **url**: YouTube 영상 URL (일반 동영상, 쇼츠 모두 지원)

### 2.3 실행 방법

```bash
cd batch_processor
python batch_clips.py
```

실행하면:
1. timestamps.csv 파일을 읽고 처리
2. 각 영상을 최고 화질로 다운로드 (이미 다운로드된 영상은 건너뜀)
3. 지정된 시간 구간으로 클립 생성
4. 분류에 따라 폴더 정리

### 2.4 설정 파일 (config.yaml)

`batch_processor/config.yaml` 파일을 수정하여 설정을 변경할 수 있습니다:

```yaml
download:
  base_directory: downloads  # 다운로드 폴더
  merge_audio_video: false   # 영상과 오디오 병합 여부

clips:
  output_directory: clips    # 클립 저장 폴더
  min_duration: 5.0          # 최소 클립 길이(초)
  max_duration: 50.0         # 최대 클립 길이(초)
  merge_clips: true          # 생성된 비디오/오디오 클립 병합 여부
  
  structure:
    labels: ['funny', 'normal', 'boring']  # 지원하는 라벨
    subdirs: ['video', 'audio', 'merged']  # 생성할 하위 폴더

batch:
  skip_existing_downloads: true  # 이미 다운로드된 영상 건너뛰기
  continue_on_error: true        # 오류 발생 시 다음 영상 계속 처리
  show_progress: true            # 진행률 표시
```

## 3. 클립 분류 기준

영상은 다음과 같은 세 가지 카테고리로 분류합니다:

### 3.1 분류 기준

| 라벨 | 짧은 코드 | 편집 관점 | 수집 기준 |
|------|---------|----------|----------|
| **funny** | f | Highlight (하이라이트) | 클라이맥스 있음 (기승전결 완성) |
| **normal** | n | Context (맥락) | 평범한 반응 (일상 대화) + 클라이맥스 없음 |
| **boring** | b | Skip (건너뛰기) | 거의 무반응 (게임 집중) |

### 3.2 클립 분류 가이드라인

#### funny (f)
- 확실한 클라이맥스가 있는 재미있는 순간
- 기승전결 구조가 완성된 영상
- 하이라이트로 사용할 수 있는 임팩트 있는 순간
- 예: 큰 웃음, 깜짝 놀람, 재미있는 반응 등

#### normal (n)
- 일상적인 대화나 평범한 반응
- 클라이맥스는 없지만 맥락 이해에 필요한 부분
- 스토리텔링에 필요한 문맥 제공 부분
- 예: 게임 설명, 일상 대화, 평범한 감정 표현 등

#### boring (b)
- 특별한 반응이 없는 부분
- 게임에만 집중하는 모습
- 편집 시 제외해도 되는 부분
- 예: 게임 플레이 집중, 침묵, 반복적인 행동 등

### 3.3 분류 시 고려사항

라벨 1(normal)과 라벨 2(funny)는 맥락적 부분에서 일부 겹칠 수 있습니다:

```
라벨 2 (funny): 40초 중 앞 20초는 맥락, 뒤 20초는 클라이맥스
라벨 1 (normal): 전체 40초가 맥락만 있음
```

이는 모델 학습 관점에서 문제가 되지 않을 것으로 예상됩니다:
- 모델은 **전체적 패턴**을 학습 (기승전결 유무)
- **시간적 변화량**이 핵심 특징이 됨
- 라벨 1은 평평한 곡선(변화량 적음), 라벨 2는 상승 곡선(맥락→클라이맥스) 패턴으로 구분 가능

## 4. 파일 구조

생성된 클립은 다음과 같은 파일명 규칙을 따릅니다:
```
{label_prefix}_{number}_{title}_{start}_{end}.mp4

예시:
f_001_본탄아메_먹는_법_20.0_27.0.mp4
n_002_급_유턴_7.0_14.0.mp4
b_003_게임_설명_35.0_42.0.mp4
```

클립은 다음 폴더 구조로 저장됩니다:
```
clips/
  ├── funny/
  │   ├── video/   # 비디오 클립
  │   ├── audio/   # 오디오 클립
  │   └── merged/  # 비디오+오디오 병합 클립
  ├── normal/
  │   ├── video/
  │   ├── audio/
  │   └── merged/
  └── boring/
      ├── video/
      ├── audio/
      └── merged/
```

## 5. 팁과 문제 해결

1. **시간 형식**: 시간은 초 단위뿐만 아니라 "분:초" 형식도 지원합니다 (예: `1:30`은 90초)
2. **중복 방지**: 같은 영상, 같은 시간대의 클립은 자동으로 건너뜁니다
3. **쇼츠 지원**: YouTube 쇼츠 URL도 지원합니다 (`https://www.youtube.com/shorts/ID`)
4. **문제 해결**: 다운로드 실패 시 `pytubefix` 라이브러리 업데이트 필요할 수 있음

---

