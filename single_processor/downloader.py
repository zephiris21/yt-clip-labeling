#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import yaml
import csv
import subprocess
from pathlib import Path
from pytubefix import YouTube
from pytubefix.cli import on_progress

def load_config(config_path="config.yaml"):
    """설정 파일 로드"""
    default_config = {
        'download': {
            'base_directory': 'downloads',
            'merge_audio_video': False
        },
        'clips': {
            'min_duration': 5.0,
            'max_duration': 7.0
        }
    }
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    else:
        # 기본 설정 파일 생성
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        print(f"✅ 기본 설정 파일 생성: {config_path}")
        return default_config

def sanitize_filename(title, max_length=80):
    """파일명 안전하게 변환"""
    # 특수문자 제거/변환
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    safe_title = safe_title.replace(' ', '_')
    safe_title = safe_title.strip('._')  # 앞뒤 특수문자 제거
    
    # 길이 제한
    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length]
    
    return safe_title

def create_timestamps_csv(video_dir, video_title, video_duration):
    """타임스탬프 CSV 템플릿 생성"""
    csv_path = os.path.join(video_dir, "timestamps.csv")
    
    # CSV 헤더와 예시 데이터
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['start', 'end', 'label'])
        writer.writerow(['# 예시: 10.5', '16.2', 'funny'])
        writer.writerow(['# 예시: 45.0', '51.5', 'normal'])
        writer.writerow(['# 주의: 클립 길이는 5-7초로 제한됩니다'])
        writer.writerow([f'# 영상 길이: {video_duration:.1f}초'])
    
    print(f"📝 타임스탬프 CSV 생성: {csv_path}")
    print(f"   파일을 열어서 start, end, label 컬럼을 채워주세요!")
    
    return csv_path

def download_youtube_video(url, config):
    """유튜브 영상 다운로드"""
    try:
        # YouTube 객체 생성
        yt = YouTube(url, on_progress_callback=on_progress)
        
        # 영상 정보 출력
        print(f"📺 제목: {yt.title}")
        print(f"⏱️  길이: {yt.length}초 ({yt.length/60:.1f}분)")
        print(f"👀 조회수: {yt.views:,}")
        
        # 안전한 파일명 생성
        safe_title = sanitize_filename(yt.title)
        print(f"📁 폴더명: {safe_title}")
        
        # 영상별 디렉토리 생성
        base_dir = config['download']['base_directory']
        video_dir = os.path.join(base_dir, safe_title)
        os.makedirs(video_dir, exist_ok=True)
        
        # 사용 가능한 스트림 확인
        print("\n🎬 사용 가능한 비디오 화질:")
        video_streams = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True)
        for stream in video_streams:
            print(f"  - {stream.resolution} ({stream.filesize_mb:.1f}MB) - {stream.fps}fps")
        
        print("\n🎵 사용 가능한 오디오 품질:")
        audio_streams = yt.streams.filter(only_audio=True)
        for stream in audio_streams:
            print(f"  - {stream.mime_type} ({stream.filesize_mb:.1f}MB) - {stream.abr}")
        
        # 최고화질 비디오 선택 (1080p 우선, adaptive only)
        video_stream = (yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True, res='1080p').first() or
                       yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True, res='720p').first() or
                       yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).get_highest_resolution())
        
        # 최고품질 오디오 선택 (m4a 우선, 없으면 webm)
        audio_stream = (yt.streams.filter(only_audio=True, file_extension='m4a').first() or
                       yt.streams.filter(only_audio=True).first())
        
        if not video_stream or not audio_stream:
            print("❌ 적절한 스트림을 찾을 수 없습니다.")
            return None
        
        print(f"\n✅ 선택된 스트림:")
        print(f"  📹 비디오: {video_stream.resolution} {video_stream.fps}fps ({video_stream.filesize_mb:.1f}MB)")
        print(f"  🎵 오디오: {audio_stream.mime_type} {audio_stream.abr} ({audio_stream.filesize_mb:.1f}MB)")
        
        # 파일명 설정 (덮어쓰기 방지)
        video_filename = f"{safe_title}_video.mp4"
        audio_filename = f"{safe_title}_audio.{audio_stream.subtype}"
        
        video_path = os.path.join(video_dir, video_filename)
        audio_path = os.path.join(video_dir, audio_filename)
        
        print(f"\n⬇️ 다운로드 시작...")
        
        # 1. 비디오 다운로드
        print("📹 비디오 다운로드 중...")
        video_stream.download(output_path=video_dir, filename=video_filename)
        print("✅ 비디오 다운로드 완료!")
        
        # 2. 오디오 다운로드
        print("🎵 오디오 다운로드 중...")
        audio_stream.download(output_path=video_dir, filename=audio_filename)
        print("✅ 오디오 다운로드 완료!")
        
        # 3. ffmpeg 병합 (옵션)
        if config['download']['merge_audio_video']:
            merged_path = os.path.join(video_dir, f"{safe_title}_merged.mp4")
            success = merge_video_audio(video_path, audio_path, merged_path)
            if success:
                print("✅ 비디오/오디오 병합 완료!")
            else:
                print("⚠️ 병합 실패 - 별도 파일로 유지됩니다.")
        
        # 4. 타임스탬프 CSV 생성
        csv_path = create_timestamps_csv(video_dir, yt.title, yt.length)
        
        print(f"\n🎉 다운로드 완료!")
        print(f"📁 저장 위치: {video_dir}")
        print(f"📝 다음 단계: {os.path.join(video_dir, 'timestamps.csv')} 파일을 편집해주세요")
        
        return {
            'video_dir': video_dir,
            'video_path': video_path,
            'audio_path': audio_path,
            'title': yt.title,
            'safe_title': safe_title,
            'duration': yt.length
        }
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def merge_video_audio(video_path, audio_path, output_path):
    """ffmpeg로 비디오와 오디오 병합"""
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-y',
            output_path
        ]
        
        # 인코딩 문제 해결을 위해 encoding 명시적 설정
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='ignore',  # 디코딩 오류 무시
            check=True
        )
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg 병합 실패: {e}")
        return False
    except FileNotFoundError:
        print("❌ ffmpeg를 찾을 수 없습니다. 설정에서 merge_audio_video를 False로 설정하세요.")
        return False
    except UnicodeDecodeError as e:
        print(f"❌ 인코딩 오류 (무시됨): {e}")
        return True  # 인코딩 오류지만 병합은 성공했을 수 있음

def main():
    """메인 실행 함수"""
    print("🎬 유튜브 영상 다운로더")
    print("=" * 50)
    
    # 설정 로드
    config = load_config()
    print(f"📋 설정 로드 완료")
    print(f"   저장 위치: {config['download']['base_directory']}")
    print(f"   ffmpeg 병합: {'활성화' if config['download']['merge_audio_video'] else '비활성화'}")
    
    # URL 입력
    url = input("\n침착맨 유튜브 URL을 입력하세요: ").strip()
    
    if not url:
        print("❌ URL이 입력되지 않았습니다.")
        return
    
    # 다운로드 실행
    result = download_youtube_video(url, config)
    
    if result:
        print("\n" + "="*50)
        print("✅ 모든 작업이 완료되었습니다!")
        print(f"📁 파일 위치: {result['video_dir']}")
        print("\n📝 다음 작업:")
        print("1. timestamps.csv 파일을 열어서 클립 정보를 입력하세요")
        print("2. 클립 생성 스크립트를 실행하세요")
    else:
        print("❌ 다운로드에 실패했습니다.")

if __name__ == "__main__":
    main()