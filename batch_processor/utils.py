#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import yaml
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
            'output_directory': 'clips',
            'min_duration': 5.0,
            'max_duration': 7.0,
            'merge_clips': True
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

def extract_video_id(url):
    """YouTube URL에서 video_id 추출"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)',
        r'youtube\.com/shorts/([^&\n?#]+)'  # YouTube Shorts 패턴 추가
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def time_to_seconds(time_str):
    """
    시간 문자열을 초로 변환
    지원 형식:
    - "11:08" → 668.0 (11분 8초)
    - "1:23:45" → 5025.0 (1시간 23분 45초)
    - "45.5" → 45.5 (이미 초 단위)
    """
    time_str = str(time_str).strip()
    
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 2:  # mm:ss
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        elif len(parts) == 3:  # hh:mm:ss
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    
    # 이미 초 단위거나 소수점 포함
    return float(time_str)

def normalize_label(label):
    """라벨 정규화 (f/F/funny -> funny, n/N/normal -> normal)"""
    if not label:
        return None
        
    label = str(label).strip().lower()
    if label in ['f', 'funny']:
        return 'funny'
    elif label in ['n', 'normal']:
        return 'normal'
    else:
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
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='ignore',
            check=True
        )
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg 병합 실패: {e}")
        return False
    except FileNotFoundError:
        print("❌ ffmpeg를 찾을 수 없습니다.")
        return False
    except UnicodeDecodeError as e:
        print(f"❌ 인코딩 오류 (무시됨): {e}")
        return True

def create_clip(video_path, audio_path, clip_data, output_paths, config):
    """ffmpeg로 클립 생성"""
    start = clip_data['start']
    end = clip_data['end']
    duration = end - start
    
    try:
        # 비디오 클립 생성
        video_cmd = [
            'ffmpeg',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            '-c:v', 'libx264',
            '-crf', '23',
            '-preset', 'fast',
            '-avoid_negative_ts', 'make_zero',
            '-y',
            output_paths['video']
        ]
        
        result = subprocess.run(
            video_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode != 0:
            return False, f"비디오 클립 생성 실패: {result.stderr}"
        
        # 오디오 클립 생성
        audio_cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-ss', str(start),
            '-t', str(duration),
            '-c:a', 'copy',
            '-avoid_negative_ts', 'make_zero',
            '-y',
            output_paths['audio']
        ]
        
        result = subprocess.run(
            audio_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode != 0:
            return False, f"오디오 클립 생성 실패: {result.stderr}"
        
        # 병합 클립 생성 (옵션)
        if config['clips'].get('merge_clips', False):
            merge_cmd = [
                'ffmpeg',
                '-i', output_paths['video'],
                '-i', output_paths['audio'],
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-y',
                output_paths['merged']
            ]
            
            result = subprocess.run(
                merge_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode != 0:
                print(f"⚠️ 병합 클립 생성 실패 (분리 파일은 유지): {result.stderr}")
        
        return True, "성공"
        
    except Exception as e:
        return False, f"클립 생성 오류: {e}"

def download_youtube_video(url, video_id, config):
    """유튜브 영상 다운로드 (수정된 버전)"""
    try:
        # YouTube 객체 생성
        yt = YouTube(url, on_progress_callback=on_progress)
        
        # 영상 정보 출력
        print(f"📺 제목: {yt.title}")
        print(f"⏱️  길이: {yt.length}초 ({yt.length/60:.1f}분)")
        
        # 영상별 디렉토리 생성 (video_id 사용)
        base_dir = config['download']['base_directory']
        video_dir = os.path.join(base_dir, video_id)
        os.makedirs(video_dir, exist_ok=True)
        
        # 최고화질 비디오 선택
        video_stream = (yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True, res='1080p').first() or
                       yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True, res='720p').first() or
                       yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).get_highest_resolution())
        
        # 최고품질 오디오 선택
        audio_stream = (yt.streams.filter(only_audio=True, file_extension='m4a').first() or
                       yt.streams.filter(only_audio=True).first())
        
        if not video_stream or not audio_stream:
            print("❌ 적절한 스트림을 찾을 수 없습니다.")
            return None
        
        # 파일명 설정
        video_filename = f"{video_id}_video.mp4"
        audio_filename = f"{video_id}_audio.{audio_stream.subtype}"
        
        video_path = os.path.join(video_dir, video_filename)
        audio_path = os.path.join(video_dir, audio_filename)
        
        print(f"⬇️ 다운로드 시작...")
        
        # 비디오 다운로드
        print("📹 비디오 다운로드 중...")
        video_stream.download(output_path=video_dir, filename=video_filename)
        
        # 오디오 다운로드
        print("🎵 오디오 다운로드 중...")
        audio_stream.download(output_path=video_dir, filename=audio_filename)
        
        print("✅ 다운로드 완료!")
        
        # 안전한 제목 생성
        safe_title = sanitize_filename(yt.title)
        
        return {
            'video_dir': video_dir,
            'video_path': video_path,
            'audio_path': audio_path,
            'title': yt.title,
            'safe_title': safe_title,
            'video_id': video_id,
            'duration': yt.length
        }
        
    except Exception as e:
        print(f"❌ 다운로드 오류: {e}")
        return None