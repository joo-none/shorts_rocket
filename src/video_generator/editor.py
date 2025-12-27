import os
import re
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

class AutoEditor:
    def __init__(self, resolution=(1920, 1080)):
        self.target_res = resolution
        self.clips = []
        self.final_clip = None
        print(f"✅ [Editor] 초기화 완료 (Target: {resolution})")

    def load_from_folder(self, folder_path: str):
        print(f"📂 폴더 로드: {folder_path}")
        if not os.path.exists(folder_path):
            print("   ❌ 폴더가 없습니다.")
            return self

        # 파일명 숫자 기준 정렬 (01.mp4 -> 02.mp4)
        files = [f for f in os.listdir(folder_path) if f.endswith(".mp4")]
        files.sort(key=lambda f: int(re.sub(r'\D', '', f)) if re.sub(r'\D', '', f).isdigit() else f)

        self.clips = []
        for f in files:
            path = os.path.join(folder_path, f)
            try:
                # MoviePy 2.0 문법: resized()
                clip = VideoFileClip(path).resized(self.target_res)
                self.clips.append(clip)
                print(f"   - 로드: {f}")
            except Exception as e:
                print(f"   ⚠️ 로드 실패 ({f}): {e}")
        return self

    def concatenate(self):
        if self.clips:
            self.final_clip = concatenate_videoclips(self.clips, method="compose")
            print(f"🎞️ 병합 완료 (길이: {self.final_clip.duration:.2f}초)")
        return self

    def add_bgm(self, music_path: str, volume=0.3):
        if self.final_clip and os.path.exists(music_path):
            print(f"🎵 BGM 추가: {music_path}")
            audio = AudioFileClip(music_path)
            
            # 루프 및 길이 조절 (MoviePy 2.0 호환)
            if audio.duration < self.final_clip.duration:
                from moviepy import concatenate_audioclips
                loops = int(self.final_clip.duration // audio.duration) + 1
                audio = concatenate_audioclips([audio] * loops)
            
            audio = audio.subclipped(0, self.final_clip.duration).with_volume_scaled(volume)
            self.final_clip = self.final_clip.with_audio(audio)
        return self

    def add_subtitles(self, subs: list, font="C:/Windows/Fonts/malgun.ttf"):
        if not self.final_clip or not subs:
            return self
        
        print("📝 자막 합성 중...")
        txt_clips = []
        for s in subs:
            # MoviePy 2.0 메서드 체이닝
            txt = (TextClip(text=s['text'], font=font, font_size=50, color='white', method='label')
                   .with_position(('center', 'bottom'))
                   .with_start(s['start'])
                   .with_duration(s['end'] - s['start']))
            txt_clips.append(txt)
            
        self.final_clip = CompositeVideoClip([self.final_clip] + txt_clips)
        return self

    def export(self, output_path: str):
        if self.final_clip:
            print(f"🚀 렌더링 시작: {output_path}")
            self.final_clip.write_videofile(
                output_path, fps=24, codec='libx264', audio_codec='aac', logger=None
            )
            print("✅ 렌더링 완료!")