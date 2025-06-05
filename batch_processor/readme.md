# YouTube 일괄 클립 생성기 사용법

## 📁 폴더 구조
```
batch_processor/
├── utils.py
├── batch_clips.py
├── config.yaml
├── timestamps.csv
├── downloads/
└── clips/
```

## 🚀 사용 방법

### 1. 파일 준비
- 위 4개 파일을 `batch_processor` 폴더에 저장

### 2. CSV 편집
`timestamps.csv` 파일을 열어서 클립 정보 입력:
```csv
url,start,end,label
https://www.youtube.com/watch?v=dQw4w9WgXcQ,10.5,16.2,funny
https://www.youtube.com/watch?v=dQw4w9WgXcQ,45.0,51.5,normal
https://www.youtube.com/watch?v=another_video,1:23,1:29,funny
```

### 3. 실행
```bash
cd batch_processor
python batch_clips.py
```

## 📝 CSV 작성 팁

- **시간 형식**: `45.5` (초) 또는 `1:23` (분:초) 또는 `1:23:45` (시:분:초)
- **라벨**: `funny`/`f` 또는 `normal`/`n`
- **클립 길이**: 5-7초로 제한 (설정에서 변경 가능)
- **주석**: `#`으로 시작하는 행은 무시됨

## 📂 결과물

- **다운로드**: `downloads/영상제목/`
- **클립**: `clips/funny/video/`, `clips/normal/video/`
- **파일명**: `f_001_영상제목_10.5_16.2.mp4`


