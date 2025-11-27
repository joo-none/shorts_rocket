import time
import os
from typing import Union, List, Optional, Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()

class VeoGenerator:
    def __init__(self, model_name: str = "veo-3.1-generate-preview"):
        self.api_key = os.getenv("GOOGLE_API_KEYLJE")
        if not self.api_key:
            raise ValueError("❌ .env 파일에서 'GOOGLE_API_KEYLJE'를 찾을 수 없습니다.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        print(f"✅ VeoGenerator 초기화 완료 ({model_name})")

    def _load_image(self, image_input: Union[str, Image.Image]) -> Image.Image:
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"❌ 이미지를 찾을 수 없습니다: {image_input}")
            return Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            return image_input
        else:
            raise ValueError("이미지는 파일 경로(str) 또는 PIL.Image 객체여야 합니다.")

    # 이 함수를 기존 코드에 덮어씌우세요
    def _wait_and_save(self, operation, output_path: str):
        print(f"   ⏳ 생성 진행 중... (타겟: {output_path})")
        
        # 1. Polling (대기)
        while not operation.done:
            time.sleep(5)
            operation = self.client.operations.get(operation)
            print(".", end="", flush=True)
        
        print(f"\n   ✨ 생성 완료! 다운로드 시도 중...")
        
        if operation.result and operation.result.generated_videos:
            video_obj = operation.result.generated_videos[0].video
            
            # [디버깅용] 만약 또 에러가 나면 이 출력 결과를 알려주세요
            # print(f"DEBUG: 객체 속성 목록: {dir(video_obj)}") 

            file_content = None
            
            # --- [시도 1] SDK 표준 방식 (문서 기반) ---
            try:
                # file 파라미터에 객체를 통째로 넘겨봅니다.
                file_content = self.client.files.download(file=video_obj)
            except Exception as e1:
                print(f"   ⚠️ [1차 시도 실패] SDK download: {e1}")

                # --- [시도 2] URI 속성을 이용한 직접 다운로드 (Fallback) ---
                try:
                    # 객체에 uri 속성이 있는지 확인
                    video_uri = getattr(video_obj, 'uri', None)
                    if video_uri:
                        print(f"   🔄 [2차 시도] URI로 직접 다운로드 시도: {video_uri}")
                        import requests
                        
                        # Google API Key를 헤더에 넣어 요청
                        response = requests.get(video_uri)
                        if response.status_code == 200:
                            file_content = response.content
                        else:
                            raise Exception(f"HTTP Error {response.status_code}")
                    else:
                        raise Exception("객체에 'uri' 속성도 없습니다.")
                        
                except Exception as e2:
                    print(f"   ❌ [2차 시도 실패] HTTP request: {e2}")
                    print(f"   🔍 디버깅 정보: {dir(video_obj)}") # 최후의 수단: 속성 출력
                    raise e2

            # 3. 파일 저장
            if file_content:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(file_content)
                print(f"   ✅ 저장 성공: {output_path}\n")
                return output_path
            else:
                raise Exception("파일 내용을 가져오지 못했습니다.")
                
        else:
            raise Exception("❌ 생성 실패: 결과물이 반환되지 않았습니다.")
        
    def generate(self, prompt: str, output_path: str = "output.mp4", image_start=None, aspect_ratio="16:9"):
        print(f"🎬 [Generate] '{prompt[:20]}...' -> {output_path}")
        
        # [안전장치] person_generation 옵션 제거 (현재 API 지원 안 함)
        config = types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            # fps=fps,
        )

        kwargs = {"model": self.model_name, "prompt": prompt, "config": config}
        
        if image_start:
            kwargs["image"] = self._load_image(image_start)
            print("   📸 시작 프레임 이미지 적용됨")

        try:
            operation = self.client.models.generate_videos(**kwargs)
            return self._wait_and_save(operation, output_path)
        except Exception as e:
            print(f"   ❌ API 요청 에러: {e}")

    # veo_generator.py 내부의 generate_batch 함수만 이걸로 덮어씌우세요
    def generate_batch(self, task_list: List[Dict], folder_name: str = "My_Project"):
        if folder_name:
            os.makedirs(folder_name, exist_ok=True)
        
        print(f"📦 [Batch] 총 {len(task_list)}개의 작업 시작")
        results = []
        
        for i, task in enumerate(task_list):
            print(f"--- 작업 {i+1}/{len(task_list)} ---")
            
            # [수정된 부분] 
            # 기존: f"scene_{i+1:03d}.mp4" (scene_001.mp4)
            # 변경: f"{i+1}.mp4" (1.mp4, 2.mp4 ...)
            # 사용자가 output_path를 지정하지 않았을 때만 작동합니다.
            filename = task.get("output_path", f"{i+1}.mp4")
            
            full_path = os.path.join(folder_name, filename)
            
            task_params = task.copy()
            task_params["output_path"] = full_path
            
            try:
                self.generate(**task_params)
                results.append(full_path)
                
                print("   💤 API 부하 방지를 위해 3초 대기...")
                time.sleep(3) 
                
            except Exception as e:
                print(f"⚠️ 작업 {i+1} 실패: {e}")
                
        print(f"🏁 배치 작업 완료. 확인: ./{folder_name}")
        return results

# --- 실행 시 주의사항 ---
if __name__ == "__main__":
    veo = VeoGenerator()
    
    # [중요] output_path를 지워야 자동 번호(1.mp4, 2.mp4)가 적용됩니다.
    tasks = [
        {"prompt": "Cyberpunk city"},     # -> 1.mp4 로 저장됨
        {"prompt": "Robot eye close up"}, # -> 2.mp4 로 저장됨
        {"prompt": "Spaceship landing"}   # -> 3.mp4 로 저장됨
    ]
    
    veo.generate_batch(tasks, folder_name="Numbered_Project")