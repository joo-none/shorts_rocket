import time
import os
import io
import requests  # 추가 필요
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from PIL import Image

class VeoGenerator:
    def __init__(self, api_key: str, model_name: str = "veo-3.1-generate-preview"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name.replace("models/", "")
        print(f"✅ VeoGenerator 초기화 (Paid Tier Mode: {self.model_name})")

    def generate_image_from_text(self, prompt: str) -> Optional[Image.Image]:
        """제공된 리스트 중 가장 성공률 높은 Imagen 4.0 모델 사용"""
        candidate_models = [
            'imagen-4.0-generate-001',      # 1순위: 정식 버전
            'imagen-4.0-fast-generate-001', # 2순위: 빠른 버전
            'imagen-4.0-generate-preview-06-06' # 3순위: 프리뷰
        ]
        
        for model_id in candidate_models:
            try:
                print(f"   🎨 이미지 생성 시도 중... ({model_id})")
                response = self.client.models.generate_images(
                    model=model_id,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(number_of_images=1)
                )
                return Image.open(io.BytesIO(response.generated_images[0].image.image_bytes))
            except Exception as e:
                print(f"   ⚠️ {model_id} 실패: {e}")
                continue
        return None

    def generate_video(self, prompt: str, output_path: str, image_start=None):
        try:
            kwargs = {
                "model": self.model_name,
                "prompt": prompt,
                "config": types.GenerateVideosConfig(aspect_ratio="9:16")
            }
            
            if image_start:
                buffered = io.BytesIO()
                image_start.save(buffered, format="JPEG")
                kwargs["image"] = types.Image(image_bytes=buffered.getvalue(), mime_type="image/jpeg")

            # 비디오 생성 작업 시작
            operation = self.client.models.generate_videos(**kwargs)
            # 완료될 때까지 기다리고 저장하는 함수 호출
            return self._wait_and_save(operation, output_path)

        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            return None

    def _wait_and_save(self, operation, output_path: str):
        """작업이 완료될 때까지 대기하고 파일을 저장합니다."""
        print(f"   ⏳ 비디오 생성 대기 중... (타겟: {output_path})")
        
        # 1. 작업 완료 여부 확인 (Polling)
        while not operation.done:
            time.sleep(5)
            operation = self.client.operations.get(operation)
            print(".", end="", flush=True)
        
        print(f"\n   ✨ 생성 완료! 다운로드 중...")
        
        # 2. 결과물 가져오기
        if operation.result and operation.result.generated_videos:
            video_obj = operation.result.generated_videos[0].video
            
            try:
                # 파일 다운로드
                file_content = self.client.files.download(file=video_obj)
                
                # 폴더 생성 및 저장
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(file_content)
                print(f"   ✅ 저장 성공: {output_path}")
                return output_path
            except Exception as e:
                print(f"   ❌ 다운로드 실패: {e}")
                return None
        else:
            print("   ❌ 생성 실패: 결과물이 없습니다.")
            return None

    def run_batch(self, tasks: List[Dict], output_folder: str):
        if not os.path.exists(output_folder): os.makedirs(output_folder)
        
        for i, task in enumerate(tasks):
            print(f"\n🎬 Clip {i+1} 시작...")
            img = self.generate_image_from_text(task.get("prompt")) if task.get("gen_image_first") else None
            
            # 여기서 비디오가 실제로 생성되어 저장될 때까지 기다립니다.
            res = self.generate_video(task.get("prompt"), os.path.join(output_folder, f"clip_{i+1}.mp4"), img)
            
            if i < len(tasks) - 1:
                print("   💤 할당량 보호를 위해 60초 대기...")
                time.sleep(60)