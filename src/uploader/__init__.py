# 파일명: src/uploader/__init__.py

# 실제 구현 파일(youtube_upload_for_main)에서 함수를 가져옵니다.
from .youtube_upload_for_main import upload_video_to_youtube

# 외부에서 import 할 수 있는 목록을 정의합니다.
__all__ = [
    "upload_video_to_youtube",
]