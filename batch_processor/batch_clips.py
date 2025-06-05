#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import glob
import re
from pathlib import Path
from collections import defaultdict
from utils import (
    load_config, extract_video_id, time_to_seconds, 
    normalize_label, download_youtube_video, create_clip
)

def parse_batch_csv(csv_path, config):
    """일괄처리용 CSV 파싱"""
    clips_data = []
    invalid_clips = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):
                # 주석 행 건너뛰기
                if any(str(value).strip().startswith('#') for value in row.values()):
                    continue
                
                try:
                    url = row['url'].strip()
                    start = time_to_seconds(row['start'])
                    end = time_to_seconds(row['end'])
                    label = normalize_label(row['label'])
                    
                    # video_id 추출
                    video_id = extract_video_id(url)
                    if not video_id:
                        invalid_clips.append(f"행 {row_num}: 잘못된 YouTube URL")
                        continue
                    
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
                    
                    clips_data.append({
                        'url': url,
                        'video_id': video_id,
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
    
    return clips_data, invalid_clips

def group_clips_by_video(clips_data):
    """video_id별로 클립 그룹핑"""
    grouped = defaultdict(list)
    
    for clip in clips_data:
        video_id = clip['video_id']
        grouped[video_id].append(clip)
    
    return dict(grouped)

def check_existing_download(video_id, config):
    """기존 다운로드 확인 (video_id와 safe_title 둘 다 확인)"""
    base_dir = config['download']['base_directory']
    
    # 1. video_id 기반 폴더 확인 (기존 다운로드)
    video_dir_by_id = os.path.join(base_dir, video_id)
    if os.path.exists(video_dir_by_id):
        video_files = glob.glob(os.path.join(video_dir_by_id, f"{video_id}_video.mp4"))
        audio_files = glob.glob(os.path.join(video_dir_by_id, f"{video_id}_audio.*"))
        if video_files and audio_files:
            return True, video_files[0], audio_files[0], video_id
    
    # 2. safe_title 기반 폴더들 확인 (새로운 방식)
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if os.path.isdir(folder_path):
            # 폴더 내에서 safe_title 기반 파일들 찾기
            video_files = glob.glob(os.path.join(folder_path, f"{folder_name}_video.mp4"))
            audio_files = glob.glob(os.path.join(folder_path, f"{folder_name}_audio.*"))
            if video_files and audio_files:
                # video_id가 일치하는지 확인 (URL에서 추출한 것과 비교)
                # 실제로는 같은 영상인지 확실하지 않으니 폴더명을 반환
                return True, video_files[0], audio_files[0], folder_name
    
    return False, None, None, None

def get_existing_clips(clips_dir):
    """기존 클립 정보 스캔"""
    existing_clips = {'funny': [], 'normal': []}
    
    for label in ['funny', 'normal']:
        video_dir = os.path.join(clips_dir, label, 'video')
        if not os.path.exists(video_dir):
            continue
            
        pattern = os.path.join(video_dir, "*.mp4")
        for video_file in glob.glob(pattern):
            clip_info = parse_clip_filename(video_file)
            if clip_info:
                existing_clips[label].append(clip_info)
    
    return existing_clips

def parse_clip_filename(filename):
    """클립 파일명에서 정보 추출"""
    basename = os.path.basename(filename)
    
    # f_001_safe_title_10.5_16.2.mp4 형식 파싱
    pattern = r'([fn])_(\d+)_(.+)_([0-9.]+)_([0-9.]+)\.mp4'
    match = re.match(pattern, basename)
    
    if match:
        label_prefix, clip_num, safe_title, start, end = match.groups()
        return {
            'label': 'funny' if label_prefix == 'f' else 'normal',
            'clip_num': int(clip_num),
            'safe_title': safe_title,
            'start': float(start),
            'end': float(end),
            'filename': basename
        }
    return None

def check_duplicate_clip(clip_data, existing_clips, safe_title):
    """중복 클립 확인"""
    label = clip_data['label']
    start = clip_data['start']
    end = clip_data['end']
    
    for existing in existing_clips[label]:
        if (existing['safe_title'] == safe_title and
            abs(existing['start'] - start) < 0.1 and
            abs(existing['end'] - end) < 0.1):
            return existing
    
    return None

def get_next_clip_number(existing_clips, label):
    """다음 클립 번호 가져오기"""
    if not existing_clips[label]:
        return 1
    
    max_num = max(clip['clip_num'] for clip in existing_clips[label])
    return max_num + 1

def process_video_clips(video_id, clips, video_path, audio_path, safe_title, config, existing_clips):
    """특정 영상의 클립들 처리"""
    stats = {'created': 0, 'skipped': 0, 'failed': 0}
    
    # 출력 디렉토리 생성
    clips_dir = config['clips']['output_directory']
    for label in ['funny', 'normal']:
        for subdir in ['video', 'audio']:
            os.makedirs(os.path.join(clips_dir, label, subdir), exist_ok=True)
        
        if config['clips'].get('merge_clips', False):
            os.makedirs(os.path.join(clips_dir, label, 'merged'), exist_ok=True)
    
    print(f"\n🎬 '{safe_title}' 클립 생성 시작... ({len(clips)}개)")
    
    for i, clip_data in enumerate(clips, 1):
        print(f"🔄 클립 {i}/{len(clips)} 처리 중... ({clip_data['start']}-{clip_data['end']}초, {clip_data['label']})")
        
        # 중복 확인
        duplicate = check_duplicate_clip(clip_data, existing_clips, safe_title)
        if duplicate:
            print(f"⚠️ 중복 클립 건너뛰기: {duplicate['filename']}")
            stats['skipped'] += 1
            continue
        
        # 클립 번호 할당
        label = clip_data['label']
        clip_num = get_next_clip_number(existing_clips, label)
        
        # 파일명 생성 (safe_title 사용)
        label_prefix = 'f' if label == 'funny' else 'n'
        base_filename = f"{label_prefix}_{clip_num:03d}_{safe_title}_{clip_data['start']}_{clip_data['end']}"
        
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
                'safe_title': safe_title,
                'start': clip_data['start'],
                'end': clip_data['end'],
                'filename': f"{base_filename}.mp4"
            })
        else:
            print(f"❌ 클립 생성 실패: {message}")
            stats['failed'] += 1
    
    return stats

def main():
    """메인 실행 함수"""
    print("🎬 YouTube 일괄 클립 생성기")
    print("=" * 50)
    
    # 설정 로드
    config = load_config()
    print(f"📋 설정 로드 완료")
    print(f"   클립 길이: {config['clips']['min_duration']}-{config['clips']['max_duration']}초")
    print(f"   클립 병합: {'활성화' if config['clips'].get('merge_clips', False) else '비활성화'}")
    
    # CSV 파일 확인
    csv_path = "timestamps.csv"
    if not os.path.exists(csv_path):
        print(f"❌ {csv_path} 파일을 찾을 수 없습니다.")
        print("   timestamps.csv 파일을 생성하고 데이터를 입력해주세요.")
        return
    
    # CSV 파싱
    print(f"\n📝 {csv_path} 파싱 중...")
    clips_data, invalid_clips = parse_batch_csv(csv_path, config)
    
    if invalid_clips:
        print("⚠️ 무시된 클립들:")
        for invalid in invalid_clips:
            print(f"   {invalid}")
    
    if not clips_data:
        print("❌ 처리할 유효한 클립이 없습니다.")
        return
    
    # 영상별 그룹핑
    grouped_clips = group_clips_by_video(clips_data)
    print(f"\n📊 총 {len(clips_data)}개 클립, {len(grouped_clips)}개 영상")
    
    # 기존 클립 스캔
    existing_clips = get_existing_clips(config['clips']['output_directory'])
    
    # 통계
    total_stats = {'downloaded': 0, 'skipped_download': 0, 'created': 0, 'skipped': 0, 'failed': 0}
    
    # 각 영상 처리
    for video_id, clips in grouped_clips.items():
        print(f"\n" + "=" * 30)
        print(f"🎥 영상 ID: {video_id}")
        print(f"📋 클립 개수: {len(clips)}개")
        
        # 기존 다운로드 확인
        exists, video_path, audio_path, existing_title = check_existing_download(video_id, config)
        
        if exists and config.get('batch', {}).get('skip_existing_downloads', True):
            print("✅ 이미 다운로드됨 - 건너뛰기")
            safe_title = existing_title  # 기존 다운로드는 video_id를 제목으로 사용
            total_stats['skipped_download'] += 1
        else:
            # 다운로드 실행
            print("⬇️ 다운로드 시작...")
            url = clips[0]['url']  # 첫 번째 클립의 URL 사용
            download_result = download_youtube_video(url, video_id, config)
            
            if not download_result:
                print("❌ 다운로드 실패 - 이 영상의 클립들을 건너뜁니다.")
                if not config.get('batch', {}).get('continue_on_error', True):
                    break
                continue
            
            video_path = download_result['video_path']
            audio_path = download_result['audio_path']
            safe_title = download_result['safe_title']
            total_stats['downloaded'] += 1
        
        # 클립 생성
        clip_stats = process_video_clips(video_id, clips, video_path, audio_path, safe_title, config, existing_clips)
        
        # 통계 합계
        for key in ['created', 'skipped', 'failed']:
            total_stats[key] += clip_stats[key]
        
        print(f"📊 영상 '{safe_title}' 완료: 생성 {clip_stats['created']}, 건너뜀 {clip_stats['skipped']}, 실패 {clip_stats['failed']}")
    
    # 최종 요약
    print(f"\n" + "=" * 50)
    print(f"🎉 일괄 처리 완료!")
    print(f"   영상 다운로드: {total_stats['downloaded']}개")
    print(f"   영상 건너뜀: {total_stats['skipped_download']}개")
    print(f"   클립 생성: {total_stats['created']}개")
    print(f"   클립 건너뜀: {total_stats['skipped']}개")
    print(f"   클립 실패: {total_stats['failed']}개")
    
    if total_stats['created'] > 0:
        clips_dir = config['clips']['output_directory']
        print(f"📁 클립 저장 위치:")
        print(f"   Funny: {os.path.join(clips_dir, 'funny', 'video')}")
        print(f"   Normal: {os.path.join(clips_dir, 'normal', 'video')}")

if __name__ == "__main__":
    main()