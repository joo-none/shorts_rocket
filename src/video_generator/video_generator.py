import os
import json
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import requests
from enum import Enum


class VideoModel(Enum):
    VEO3 = "veo3"
    SORA2 = "sora2"


@dataclass
class VideoGenerationRequest:
    prompt: str
    visual_description: str
    duration: int
    style: str
    model: VideoModel
    resolution: str = "1920x1080"
    fps: int = 30


@dataclass
class GeneratedVideo:  # 건희 구현
    video_path: str
    thumbnail_path: Optional[str]
    metadata: Dict[str, Any]
    generation_time: float
    model_used: VideoModel
    created_at: str


class VideoGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.setup_api_clients()

    def setup_api_clients(self):
        """API 클라이언트 설정"""
        self.veo3_config = self.config.get("veo3", {})
        self.sora2_config = self.config.get("sora2", {})

        # Gemini/VEO3 설정
        self.gemini_api_key = self.veo3_config.get(
            "api_key", os.getenv("GEMINI_API_KEY")
        )

        # SORA2 설정 (OpenAI)
        self.openai_api_key = self.sora2_config.get(
            "api_key", os.getenv("OPENAI_API_KEY")
        )

    def generate_video(
        self, request: VideoGenerationRequest
    ) -> Optional[GeneratedVideo]:
        """비디오 생성 메인 함수"""
        start_time = time.time()

        try:
            if request.model == VideoModel.VEO3:
                video_path = self._generate_with_veo3(request)
            elif request.model == VideoModel.SORA2:
                video_path = self._generate_with_sora2(request)
            else:
                raise ValueError(f"Unsupported model: {request.model}")

            if not video_path:
                return None

            generation_time = time.time() - start_time

            # 썸네일 생성
            thumbnail_path = self._generate_thumbnail(video_path)

            # 메타데이터 생성
            metadata = {
                "prompt": request.prompt,
                "visual_description": request.visual_description,
                "duration": request.duration,
                "style": request.style,
                "resolution": request.resolution,
                "fps": request.fps,
                "model": request.model.value,
                "generation_time": generation_time,
            }

            return GeneratedVideo(
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                metadata=metadata,
                generation_time=generation_time,
                model_used=request.model,
                created_at=datetime.now().isoformat(),
            )

        except Exception as e:
            logging.error(f"Video generation failed: {e}")
            return None

    def _generate_with_veo3(self, request: VideoGenerationRequest) -> Optional[str]:
        """VEO3로 비디오 생성"""
        try:
            # VEO3 API 엔드포인트 (실제 구현 시 정확한 엔드포인트로 수정 필요)
            url = (
                "https://generativelanguage.googleapis.com/v1/models/veo3:generateVideo"
            )

            headers = {
                "Authorization": f"Bearer {self.gemini_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "prompt": self._format_prompt_for_veo3(request),
                "duration": request.duration,
                "resolution": request.resolution,
                "style": request.style,
            }

            response = requests.post(url, headers=headers, json=payload, timeout=300)

            if response.status_code == 200:
                result = response.json()
                video_url = result.get("video_url")

                if video_url:
                    return self._download_video(video_url, "veo3")

            logging.error(f"VEO3 API error: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logging.error(f"VEO3 generation error: {e}")
            return None

    def _generate_with_sora2(self, request: VideoGenerationRequest) -> Optional[str]:
        """SORA2로 비디오 생성"""
        try:
            # SORA2 API 엔드포인트 (실제 구현 시 정확한 엔드포인트로 수정 필요)
            url = "https://api.openai.com/v1/video/generations"

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "sora-2",
                "prompt": self._format_prompt_for_sora2(request),
                "duration": request.duration,
                "resolution": request.resolution,
                "quality": "high",
            }

            response = requests.post(url, headers=headers, json=payload, timeout=300)

            if response.status_code == 200:
                result = response.json()
                video_url = result.get("data", [{}])[0].get("url")

                if video_url:
                    return self._download_video(video_url, "sora2")

            logging.error(f"SORA2 API error: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logging.error(f"SORA2 generation error: {e}")
            return None

    def _format_prompt_for_veo3(self, request: VideoGenerationRequest) -> str:
        """VEO3용 프롬프트 포맷팅"""
        return f"""
        {request.visual_description}
        
        Video Requirements:
        - Duration: {request.duration} seconds
        - Style: {request.style}
        - Resolution: {request.resolution}
        - Format: Vertical video suitable for YouTube Shorts
        
        Content: {request.prompt}
        """

    def _format_prompt_for_sora2(self, request: VideoGenerationRequest) -> str:
        """SORA2용 프롬프트 포맷팅"""
        return f"""
        Create a {request.duration}-second video with the following specifications:
        
        Visual Style: {request.visual_description}
        Content Style: {request.style}
        
        Script/Content: {request.prompt}
        
        Technical requirements:
        - Vertical aspect ratio (9:16) for shorts format
        - High quality, professional appearance
        - Smooth transitions and clear audio
        """

    def _download_video(self, video_url: str, model_prefix: str) -> str:
        """생성된 비디오 다운로드"""
        try:
            response = requests.get(video_url, stream=True, timeout=120)
            response.raise_for_status()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{model_prefix}_video_{timestamp}.mp4"
            filepath = os.path.join("data/videos", filename)

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logging.info(f"Video downloaded: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Video download error: {e}")
            return None

    def _generate_thumbnail(self, video_path: str) -> Optional[str]:
        """비디오 썸네일 생성"""
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)

            # 비디오 중간 지점에서 프레임 추출
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            middle_frame = frame_count // 2

            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
            ret, frame = cap.read()

            if ret:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                thumbnail_filename = f"thumbnail_{timestamp}.jpg"
                thumbnail_path = os.path.join("data/thumbnails", thumbnail_filename)

                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                cv2.imwrite(thumbnail_path, frame)

                cap.release()
                return thumbnail_path

            cap.release()
            return None

        except ImportError:
            logging.warning("OpenCV not available for thumbnail generation")
            return None
        except Exception as e:
            logging.error(f"Thumbnail generation error: {e}")
            return None

    def save_video_metadata(self, video: GeneratedVideo, filename: str):
        """비디오 메타데이터 저장"""
        metadata = {
            "video_path": video.video_path,
            "thumbnail_path": video.thumbnail_path,
            "metadata": video.metadata,
            "generation_time": video.generation_time,
            "model_used": video.model_used.value,
            "created_at": video.created_at,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logging.info(f"Video metadata saved to {filename}")


class VideoGeneratorFactory:
    """비디오 생성기 팩토리 클래스"""

    @staticmethod
    def create_generator(config_path: str) -> VideoGenerator:
        """설정 파일로부터 VideoGenerator 인스턴스 생성"""
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        return VideoGenerator(config)

    @staticmethod
    def get_best_model(priority: list = None) -> VideoModel:
        """사용 가능한 최적 모델 반환"""
        if priority is None:
            priority = [VideoModel.VEO3, VideoModel.SORA2]

        # 실제 구현에서는 API 키 존재 여부, 크레딧 잔액 등을 확인
        for model in priority:
            if model == VideoModel.VEO3:
                if os.getenv("GEMINI_API_KEY"):
                    return model
            elif model == VideoModel.SORA2:
                if os.getenv("OPENAI_API_KEY"):
                    return model

        return VideoModel.VEO3  # 기본값


if __name__ == "__main__":
    # 테스트 예제
    config = {
        "veo3": {"api_key": "your_gemini_key"},
        "sora2": {"api_key": "your_openai_key"},
    }

    generator = VideoGenerator(config)

    request = VideoGenerationRequest(
        prompt="일론 머스크가 비트코인에 대해 설명하는 영상",
        visual_description="미래적인 배경에서 일론 머스크가 설명하는 모습",
        duration=60,
        style="futuristic_tech_style",
        model=VideoModel.VEO3,
    )

    result = generator.generate_video(request)
    if result:
        print(f"Video generated successfully: {result.video_path}")
    else:
        print("Video generation failed")
