import os
import json
import logging
import pickle
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


@dataclass
class YouTubeVideo:
    title: str
    description: str
    tags: List[str]
    category_id: str = "22"  # People & Blogs
    privacy_status: str = "private"  # private, unlisted, public
    made_for_kids: bool = False


@dataclass
class UploadResult:
    video_id: Optional[str]
    video_url: Optional[str]
    success: bool
    error_message: Optional[str]
    uploaded_at: str


class YouTubeUploader:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    def __init__(self, credentials_path: str = "config/youtube_credentials.json"):
        self.credentials_path = credentials_path
        self.token_path = "config/youtube_token.pickle"
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """YouTube API 인증"""
        creds = None

        # 저장된 토큰이 있으면 로드
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        # 토큰이 없거나 만료되었으면 새로 발급
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=8080)

            # 토큰 저장
            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)

        # YouTube API 서비스 객체 생성
        self.service = build(self.API_SERVICE_NAME, self.API_VERSION, credentials=creds)
        logging.info("YouTube API authentication successful")

    def upload_video(
        self,
        video_path: str,
        video_info: YouTubeVideo,
        thumbnail_path: Optional[str] = None,
    ) -> UploadResult:
        """YouTube에 비디오 업로드"""
        try:
            # 비디오 메타데이터 설정
            body = {
                "snippet": {
                    "title": video_info.title,
                    "description": video_info.description,
                    "tags": video_info.tags,
                    "categoryId": video_info.category_id,
                },
                "status": {
                    "privacyStatus": video_info.privacy_status,
                    "selfDeclaredMadeForKids": video_info.made_for_kids,
                },
            }

            # 비디오 파일 업로드
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

            insert_request = self.service.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            # 업로드 실행
            response = self._execute_upload(insert_request)

            if response:
                video_id = response["id"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # 썸네일 업로드 (있는 경우)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    self._upload_thumbnail(video_id, thumbnail_path)

                logging.info(f"Video uploaded successfully: {video_url}")

                return UploadResult(
                    video_id=video_id,
                    video_url=video_url,
                    success=True,
                    error_message=None,
                    uploaded_at=datetime.now().isoformat(),
                )
            else:
                return UploadResult(
                    video_id=None,
                    video_url=None,
                    success=False,
                    error_message="Upload failed - no response",
                    uploaded_at=datetime.now().isoformat(),
                )

        except HttpError as e:
            error_msg = f"HTTP error occurred: {e}"
            logging.error(error_msg)
            return UploadResult(
                video_id=None,
                video_url=None,
                success=False,
                error_message=error_msg,
                uploaded_at=datetime.now().isoformat(),
            )
        except Exception as e:
            error_msg = f"Unexpected error occurred: {e}"
            logging.error(error_msg)
            return UploadResult(
                video_id=None,
                video_url=None,
                success=False,
                error_message=error_msg,
                uploaded_at=datetime.now().isoformat(),
            )

    def _execute_upload(self, insert_request):
        """업로드 실행 및 진행률 모니터링"""
        response = None
        error = None
        retry = 0

        while response is None:
            try:
                logging.info("Uploading video...")
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logging.info(f"Upload progress: {progress}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    error = (
                        f"A retriable HTTP error {e.resp.status} occurred: {e.content}"
                    )
                    logging.warning(error)
                    retry += 1
                    if retry > 3:
                        break
                else:
                    raise
            except Exception as e:
                error = f"An error occurred: {e}"
                logging.error(error)
                break

        if response is not None:
            if "id" in response:
                return response
            else:
                logging.error(f"Upload failed with unexpected response: {response}")
        else:
            if error:
                logging.error(f"Upload failed: {error}")

        return None

    def _upload_thumbnail(self, video_id: str, thumbnail_path: str):
        """비디오 썸네일 업로드"""
        try:
            media = MediaFileUpload(thumbnail_path)
            self.service.thumbnails().set(videoId=video_id, media_body=media).execute()
            logging.info(f"Thumbnail uploaded for video {video_id}")
        except Exception as e:
            logging.error(f"Thumbnail upload failed: {e}")

    def update_video_info(self, video_id: str, updates: Dict[str, Any]) -> bool:
        """업로드된 비디오 정보 업데이트"""
        try:
            # 현재 비디오 정보 가져오기
            response = (
                self.service.videos().list(part="snippet,status", id=video_id).execute()
            )

            if not response["items"]:
                logging.error(f"Video with ID {video_id} not found")
                return False

            video = response["items"][0]

            # 업데이트할 정보 적용
            if "title" in updates:
                video["snippet"]["title"] = updates["title"]
            if "description" in updates:
                video["snippet"]["description"] = updates["description"]
            if "tags" in updates:
                video["snippet"]["tags"] = updates["tags"]
            if "privacy_status" in updates:
                video["status"]["privacyStatus"] = updates["privacy_status"]

            # 업데이트 실행
            self.service.videos().update(part="snippet,status", body=video).execute()

            logging.info(f"Video {video_id} updated successfully")
            return True

        except Exception as e:
            logging.error(f"Video update failed: {e}")
            return False

    def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """업로드된 비디오 정보 조회"""
        try:
            response = (
                self.service.videos()
                .list(part="snippet,status,statistics", id=video_id)
                .execute()
            )

            if response["items"]:
                return response["items"][0]
            else:
                logging.error(f"Video with ID {video_id} not found")
                return None

        except Exception as e:
            logging.error(f"Video info retrieval failed: {e}")
            return None

    def delete_video(self, video_id: str) -> bool:
        """비디오 삭제"""
        try:
            self.service.videos().delete(id=video_id).execute()
            logging.info(f"Video {video_id} deleted successfully")
            return True
        except Exception as e:
            logging.error(f"Video deletion failed: {e}")
            return False


class YouTubeVideoBuilder:
    """YouTube 비디오 정보 빌더 클래스"""

    def __init__(self):
        self.reset()

    def reset(self):
        self._title = ""
        self._description = ""
        self._tags = []
        self._category_id = "22"
        self._privacy_status = "private"
        self._made_for_kids = False
        return self

    def title(self, title: str):
        self._title = title
        return self

    def description(self, description: str):
        self._description = description
        return self

    def tags(self, tags: List[str]):
        self._tags = tags
        return self

    def add_tag(self, tag: str):
        if tag not in self._tags:
            self._tags.append(tag)
        return self

    def category_id(self, category_id: str):
        self._category_id = category_id
        return self

    def privacy_status(self, status: str):
        if status in ["private", "unlisted", "public"]:
            self._privacy_status = status
        return self

    def made_for_kids(self, is_for_kids: bool):
        self._made_for_kids = is_for_kids
        return self

    def build(self) -> YouTubeVideo:
        return YouTubeVideo(
            title=self._title,
            description=self._description,
            tags=self._tags,
            category_id=self._category_id,
            privacy_status=self._privacy_status,
            made_for_kids=self._made_for_kids,
        )


def create_financial_video_info(
    title: str, content: str, character: str
) -> YouTubeVideo:
    """금융 뉴스 비디오용 YouTube 정보 생성"""
    builder = YouTubeVideoBuilder()

    description = f"""
{content}

📈 최신 금융 뉴스를 {character}가 알려드립니다!

🔔 구독과 좋아요, 알림설정 부탁드립니다!

#금융뉴스 #투자 #{character} #경제뉴스 #shorts
    """.strip()

    tags = [
        "금융뉴스",
        "투자",
        "경제",
        "주식",
        "암호화폐",
        character,
        "shorts",
        "뉴스분석",
        "경제뉴스",
    ]

    return (
        builder.title(title)
        .description(description)
        .tags(tags)
        .category_id("25")  # News & Politics
        .privacy_status("private")
        .made_for_kids(False)
        .build()
    )


if __name__ == "__main__":
    # 테스트 예제
    uploader = YouTubeUploader()

    video_info = create_financial_video_info(
        title="🚀 일론 머스크가 알려주는: 비트코인 급등 분석",
        content="비트코인이 새로운 고점을 기록했습니다...",
        character="일론머스크",
    )

    # result = uploader.upload_video("path/to/video.mp4", video_info)
    print("YouTube uploader initialized successfully")
