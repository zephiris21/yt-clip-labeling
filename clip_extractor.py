#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import csv
import yaml
import glob
import subprocess
from pathlib import Path

def load_config(config_path="config.yaml"):
    """설정 파일 로드"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
        return None

def scan_video_folders(base_dir):
    """영상 폴더 스캔 및 CSV 상태 확인"""
    if not os.path.exists(base_dir):
        print(f"❌ 디렉토리를 찾을 수 없습니다: {base_dir}")
        return []
    
    video_folders = []
    for item in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, item)
        if os.path.isdir(folder_path) and item not in ['funny', 'normal']:
            csv_path = os.path.join(folder_path, 'timestamps.csv')
            
            # CSV 상태 확인
            csv_status = check_csv_status(csv_path)
            video_folders.append({
                'name': item,
                'path': folder_path,
                'csv_path': csv_path,
                'status': csv_status
            })
    
    return video_folders

def check_csv_status(csv_path):
    """CSV 파일 상태 확인"""
    if not os.path.exists(csv_path):
        return 'missing'
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 실제 데이터 행 개수 확인 (주석과 헤더 제외)
        data_lines = [line for line in lines if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('start')]
        
        if len(data_lines) == 0:
            return 'empty'
        else:
            return 'ready'
            
    except Exception as e:
        return 'error'

def parse_csv_data(csv_path, config):
    """CSV 데이터 파싱 및 유효성 검사"""
    valid_clips = []
    invalid_clips = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # 헤더 다음부터
                # 주석 행 건너뛰기
                if any(str(value).strip().startswith('#') for value in row.values()):
                    continue
                
                try:
                    start = float(row['start'])
                    end = float(row['end'])
                    label = normalize_label(row['label'])
                    
                    # 유효성 검사
                    duration = end - start
                    min_dur = config['clips']['min_duration']
                    max_dur = config['clips']['max_duration']
                    
                    if label is None:
                        invalid_clips.append(f"행 {row_num}: 잘못된 라벨 '{row['label']}'")
                        continue
                        
                    if duration < min_dur or duration > max_dur:
                        invalid_clips.append(f"행 {row_num}: 클립 길이 {duration:.1f}초 (허용: {min_dur}-{max_dur}초)")
                        continue
                    
                    if start >= end:
                        invalid_clips.append(f"행 {row_num}: 시작시간이 종료시간보다 큼")
                        continue
                    
                    valid_clips.append({
                        'start': start,
                        'end': end,
                        'label': label,
                        'duration': duration,
                        'row_num': row_num
                    })
                    
                except (ValueError, KeyError) as e:
                    invalid_clips.append(f"행 {row_num}: 데이터 파싱 오류 ({e})")
                    
    except Exception as e:
        print(f"❌ CSV 읽기 오류: {e}")
        return [], []
    
    return valid_clips, invalid_clips

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

def get_existing_clips(base_dir):
    """기존 클립 정보 스캔"""
    existing_clips = {'funny': [], 'normal': []}
    
    for label in ['funny', 'normal']:
        video_dir = os.path.join(base_dir, label, 'video')
        if not os.path.exists(video_dir):
            continue
            
        # video 폴더 내의 mp4 파일들 스캔
        pattern = os.path.join(video_dir, "*.mp4")
        for video_file in glob.glob(pattern):
            clip_info = parse_clip_filename(video_file)
            if clip_info:
                existing_clips[label].append(clip_info)
    
    return existing_clips

def parse_clip_filename(filename):
    """클립 파일명에서 정보 추출"""
    # f_001_영상명_10.5_16.2.mp4 형식 파싱 (video 폴더 내)
    basename = os.path.basename(filename)
    
    # 정규식으로 파싱
    pattern = r'([fn])_(\d+)_(.+)_([0-9.]+)_([0-9.]+)\.mp4'
    match = re.match(pattern, basename)
    
    if match:
        label_prefix, clip_num, video_name, start, end = match.groups()
        return {
            'label': 'funny' if label_prefix == 'f' else 'normal',
            'clip_num': int(clip_num),
            'video_name': video_name,
            'start': float(start),
            'end': float(end),
            'filename': basename
        }
    return None

def check_duplicate_clip(clip_data, existing_clips, video_name):
    """중복 클립 확인"""
    label = clip_data['label']
    start = clip_data['start']
    end = clip_data['end']
    
    for existing in existing_clips[label]:
        if (existing['video_name'] == video_name and
            abs(existing['start'] - start) < 0.1 and  # 0.1초 오차 허용
            abs(existing['end'] - end) < 0.1):
            return existing
    
    return None

def get_next_clip_number(existing_clips, label):
    """다음 클립 번호 가져오기"""
    if not existing_clips[label]:
        return 1
    
    max_num = max(clip['clip_num'] for clip in existing_clips[label])
    return max_num + 1

def create_clip(video_path, audio_path, clip_data, output_paths, config):
    """ffmpeg로 클립 생성"""
    start = clip_data['start']
    end = clip_data['end']
    duration = end - start
    
    try:
        # 비디오 클립 생성
        video_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(start),
            '-t', str(duration),
            '-c:v', 'copy',
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

def process_video_clips(video_info, config):
    """영상의 클립들 처리"""
    video_name = video_info['name']
    video_folder = video_info['path']
    csv_path = video_info['csv_path']
    
    print(f"\n🎬 '{video_name}' 처리 시작...")
    
    # CSV 데이터 파싱
    valid_clips, invalid_clips = parse_csv_data(csv_path, config)
    
    if invalid_clips:
        print("⚠️ 무시된 클립들:")
        for invalid in invalid_clips:
            print(f"   {invalid}")
    
    if not valid_clips:
        print("❌ 처리할 유효한 클립이 없습니다.")
        return {'created': 0, 'skipped': 0, 'failed': 0}
    
    print(f"📋 총 {len(valid_clips)}개 클립 처리 예정")
    
    # 영상/오디오 파일 찾기
    video_files = glob.glob(os.path.join(video_folder, "*_video.mp4"))
    audio_files = glob.glob(os.path.join(video_folder, "*_audio.*"))
    
    if not video_files or not audio_files:
        print("❌ 영상 또는 오디오 파일을 찾을 수 없습니다.")
        return {'created': 0, 'skipped': 0, 'failed': 0}
    
    video_path = video_files[0]
    audio_path = audio_files[0]
    
    # 기존 클립 스캔
    clips_dir = config['clips']['output_directory']
    existing_clips = get_existing_clips(clips_dir)
    
    # 출력 디렉토리 생성
    for label in ['funny', 'normal']:
        for subdir in ['video', 'audio']:
            os.makedirs(os.path.join(clips_dir, label, subdir), exist_ok=True)
        
        # merged 폴더는 옵션에 따라 생성
        if config['clips'].get('merge_clips', False):
            os.makedirs(os.path.join(clips_dir, label, 'merged'), exist_ok=True)
    
    # 통계
    stats = {'created': 0, 'skipped': 0, 'failed': 0}
    
    # 각 클립 처리
    for i, clip_data in enumerate(valid_clips, 1):
        print(f"🔄 클립 {i}/{len(valid_clips)} 처리 중... ({clip_data['start']}-{clip_data['end']}초)")
        
        # 중복 확인
        duplicate = check_duplicate_clip(clip_data, existing_clips, video_name)
        if duplicate:
            print(f"⚠️ 중복 클립 발견: {duplicate['filename']}")
            action = input("   1. 건너뛰기  2. 덮어쓰기  선택 (1/2): ").strip()
            if action != '2':
                print("   건너뛰기")
                stats['skipped'] += 1
                continue
        
        # 클립 번호 할당
        label = clip_data['label']
        clip_num = get_next_clip_number(existing_clips, label)
        
        # 파일명 생성 (확장자 제거)
        label_prefix = 'f' if label == 'funny' else 'n'
        base_filename = f"{label_prefix}_{clip_num:03d}_{video_name}_{clip_data['start']}_{clip_data['end']}"
        
        output_paths = {
            'video': os.path.join(clips_dir, label, 'video', f"{base_filename}.mp4"),
            'audio': os.path.join(clips_dir, label, 'audio', f"{base_filename}{Path(audio_path).suffix}"),
        }
        
        if config['clips'].get('merge_clips', False):
            output_paths['merged'] = os.path.join(clips_dir, label, 'merged', f"{base_filename}.mp4")
        
        # 클립 생성
        success, message = create_clip(video_path, audio_path, clip_data, output_paths, config)
        
        if success:
            print(f"✅ {base_filename} 생성 완료")
            stats['created'] += 1
            
            # 기존 클립 목록 업데이트
            existing_clips[label].append({
                'label': label,
                'clip_num': clip_num,
                'video_name': video_name,
                'start': clip_data['start'],
                'end': clip_data['end'],
                'filename': f"{base_filename}_video.mp4"
            })
        else:
            print(f"❌ 클립 생성 실패: {message}")
            stats['failed'] += 1
    
    return stats

def select_videos_to_process(video_folders):
    """처리할 영상 선택"""
    print("\n🎬 클립 생성기")
    print("=" * 50)
    
    # 상태별 분류
    ready_videos = [v for v in video_folders if v['status'] == 'ready']
    
    if not ready_videos:
        print("❌ 처리 가능한 영상이 없습니다.")
        print("   timestamps.csv 파일을 확인해주세요.")
        return []
    
    print(f"📋 처리 가능한 영상: {len(ready_videos)}개")
    for i, video in enumerate(ready_videos, 1):
        print(f"   {i}. {video['name']}")
    
    print(f"\n선택 옵션:")
    print(f"   0. 모든 영상 자동 처리")
    print(f"   1-{len(ready_videos)}. 개별 영상 선택")
    
    try:
        choice = input(f"\n선택 (0-{len(ready_videos)}): ").strip()
        
        if choice == '0':
            return ready_videos
        
        choice_num = int(choice)
        if 1 <= choice_num <= len(ready_videos):
            return [ready_videos[choice_num - 1]]
        else:
            print("❌ 잘못된 선택입니다.")
            return []
            
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        return []

def main():
    """메인 실행 함수"""
    # 설정 로드
    config = load_config()
    if not config:
        return
    
    print(f"📋 설정 로드 완료")
    print(f"   클립 길이: {config['clips']['min_duration']}-{config['clips']['max_duration']}초")
    print(f"   클립 병합: {'활성화' if config['clips'].get('merge_clips', False) else '비활성화'}")
    
    # 영상 폴더 스캔
    base_dir = config['download']['base_directory']
    video_folders = scan_video_folders(base_dir)
    
    if not video_folders:
        print("❌ 처리할 영상 폴더가 없습니다.")
        return
    
    # 처리할 영상 선택
    selected_videos = select_videos_to_process(video_folders)
    
    if not selected_videos:
        print("❌ 선택된 영상이 없습니다.")
        return
    
    # 선택된 영상들 처리
    total_stats = {'created': 0, 'skipped': 0, 'failed': 0}
    
    for video_info in selected_videos:
        stats = process_video_clips(video_info, config)
        for key in total_stats:
            total_stats[key] += stats[key]
    
    # 최종 요약
    print(f"\n" + "=" * 50)
    print(f"✅ 모든 처리 완료!")
    print(f"   생성됨: {total_stats['created']}개")
    print(f"   건너뜀: {total_stats['skipped']}개")
    print(f"   실패함: {total_stats['failed']}개")
    
    if total_stats['created'] > 0:
        clips_dir = config['clips']['output_directory']
        funny_video_dir = os.path.join(clips_dir, 'funny', 'video')
        normal_video_dir = os.path.join(clips_dir, 'normal', 'video')
        print(f"📁 클립 저장 위치: {funny_video_dir}, {normal_video_dir}")
        if config['clips'].get('merge_clips', False):
            print(f"   병합 클립: clips/funny/merged, clips/normal/merged")

if __name__ == "__main__":
    main()