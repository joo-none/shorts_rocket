import os
# [변경 1] moviepy.editor가 사라졌으므로 직접 import
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
# [변경 2] fx 모듈 import 경로 변경 (all 제거)
import moviepy.video.fx as vfx
import re

class AutoEditor:
    def __init__(self, output_resolution=(1920, 1080)):
        self.target_res = output_resolution
        self.clips = []
        self.final_clip = None

    def load_clips_from_folder(self, folder_path, sort_by_name=True):
        print(f"📂 '{folder_path}' 폴더에서 영상 로드 중...")
        
        files = [f for f in os.listdir(folder_path) if f.endswith(".mp4")]
        
        if sort_by_name:
            # [핵심 수정] 숫자 기준 자연 정렬(Natural Sort) 로직 적용
            # 1.mp4 -> 2.mp4 -> 10.mp4 순서가 보장됩니다.
            files.sort(key=lambda f: int(re.sub('\D', '', f)) if re.sub('\D', '', f).isdigit() else f)
            
            # 설명: 파일명에서 숫자만 추출('1', '10')해서 정수로 변환 후 크기 비교
            
        loaded_clips = []
        for filename in files:
            path = os.path.join(folder_path, filename)
            clip = VideoFileClip(path)
            
            # [변경 3] resize() -> resized() 메서드 사용
            # MoviePy 2.0에서는 'resized' 메서드가 직접 제공됩니다.
            clip_resized = clip.resized(self.target_res)
            
            loaded_clips.append(clip_resized)
            print(f"   - 로드됨: {filename} ({clip.duration:.2f}초)")
            
        self.clips = loaded_clips
        return self

    def concatenate(self):
        if not self.clips:
            raise ValueError("로드된 영상이 없습니다.")

        print("🎞️ 영상 이어붙이기 진행 중...")
        # [변경 4] concatenate_videoclips는 유지되나 method='compose'가 더 안정적
        self.final_clip = concatenate_videoclips(self.clips, method="compose")
        print(f"   - 전체 길이: {self.final_clip.duration:.2f}초")
        return self

    def add_background_music(self, music_path, volume=0.5, fade_out=2):
        if not self.final_clip:
            raise ValueError("영상이 먼저 병합되어야 합니다.")
            
        print(f"🎵 배경음악 추가: {music_path}")
        
        audio = AudioFileClip(music_path)
        
        # 음악 반복 및 자르기
        if audio.duration < self.final_clip.duration:
            loops = int(self.final_clip.duration // audio.duration) + 1
            # [변경 5] loop -> looped (또는 with_effects 사용)
            # 2.0 최신 빌드에서는 looped() 메서드를 지원하거나, 
            # 안되면 아래처럼 리스트 곱셈으로 해결하는 것이 가장 안전합니다.
            # audio = audio.looped(loops) (버전에 따라 안될 수 있음)
            from moviepy import concatenate_audioclips
            audio = concatenate_audioclips([audio] * loops)
            
        # [변경 6] subclip -> subclipped
        audio = audio.subclipped(0, self.final_clip.duration)
        
        # [변경 7] volumex -> with_volume_scaled
        audio = audio.with_volume_scaled(volume)
        
        # [변경 8] audio_fadeout -> with_effects([vfx.AudioFadeOut(...)])
        # 복잡성을 줄이기 위해 fade_out은 일단 제외하거나 아래 방식 사용
        # audio = audio.with_effects([vfx.AudioFadeOut(duration=fade_out)])
        
        # [변경 9] set_audio -> with_audio
        self.final_clip = self.final_clip.with_audio(audio)
        return self

    def add_subtitles(self, subtitles_list, font_path="malgun.ttf", fontsize=50, color='white'):
        if not self.final_clip:
            raise ValueError("영상이 먼저 병합되어야 합니다.")
            
        print("📝 자막 생성 및 합성 중...")
        
        text_clips = []
        for sub in subtitles_list:
            # [변경 10] TextClip 초기화 파라미터 변경 (snake_case 적용)
            # fontsize -> font_size
            # font에는 시스템 폰트 경로를 정확히 넣는 것을 권장
            txt_clip = (TextClip(
                            text=sub['text'], 
                            font=font_path, 
                            font_size=fontsize, 
                            color=color, 
                            method='label'
                        )
                        # [변경 11] set_position -> with_position
                        .with_position(('center', 'bottom'))
                        # [변경 12] set_start -> with_start
                        .with_start(sub['start'])
                        # [변경 13] set_duration -> with_duration
                        .with_duration(sub['end'] - sub['start']))
            
            text_clips.append(txt_clip)
            
        self.final_clip = CompositeVideoClip([self.final_clip] + text_clips)
        return self

    def export(self, output_path, fps=24):
        if not self.final_clip:
            raise ValueError("내보낼 영상이 없습니다.")
            
        print(f"🚀 최종 렌더링 시작: {output_path}")
        self.final_clip.write_videofile(
            output_path, 
            fps=fps, 
            codec='libx264', 
            audio_codec='aac',
            threads=4
        )
        print("✅ 작업 완료!")

# --- 실행부 (변경 없음) ---
if __name__ == "__main__":
    editor = AutoEditor(output_resolution=(1920, 1080))
    
    # (폴더명, 파일명 등은 본인 환경에 맞게 수정하세요)
    video_folder = "Final_Test_Folder"  
    
    if os.path.exists(video_folder):
        editor.load_clips_from_folder(video_folder)
        editor.concatenate()
        
        # 음악 파일이 없으면 에러나므로 예시 경로 확인 필요
        # editor.add_background_music("bgm.mp3") 
        
        subs = [
            {"start": 0, "end": 3, "text": "첫 번째 장면입니다."},
            {"start": 3, "end": 6, "text": "두 번째 장면으로 넘어갑니다."},
        ]
        
        # 자막 폰트 경로 주의 (Windows 예시)
        try:
            editor.add_subtitles(subs, font_path="C:/Windows/Fonts/malgun.ttf")
        except Exception as e:
            print(f"⚠️ 자막 건너뜀: {e}")

        editor.export("final_result_v2.mp4")
    else:
        print(f"❌ 폴더 없음: {video_folder}")