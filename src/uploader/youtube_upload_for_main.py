"""
YouTube 업로드 모듈 (Main 통합용)
작성자: 강산
설명: main.py에서 import하여 사용할 수 있는 YouTube 업로드 함수들
"""

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

# YouTube API 인증 범위
YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def youtube_authenticate():
    """
    YouTube API 인증 및 서비스 객체 반환

    Returns:
        youtube service: YouTube API 서비스 객체
    """
    creds = None

    # 기존 토큰 파일이 있는지 확인
    if os.path.exists("token_youtube.json"):
        creds = Credentials.from_authorized_user_file("token_youtube.json", YT_SCOPES)

    # 토큰이 없거나 만료된 경우 새로 인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  🔄 YouTube 토큰 갱신 중...")
            creds.refresh(Request())
        else:
            print("  🔐 YouTube 인증 시작...")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials_youtube.json", YT_SCOPES
            )
            creds = flow.run_local_server(port=8080)

        # 토큰 저장
        with open("token_youtube.json", "w") as token:
            token.write(creds.to_json())
        print("  ✅ YouTube 토큰 저장 완료!")

    return build("youtube", "v3", credentials=creds)


def upload_video_to_youtube(
    video_path, title, description, tags=None, privacy="unlisted"
):
    """
    YouTube에 영상 업로드

    Args:
        video_path (str): 업로드할 영상 파일 경로
        title (str): 영상 제목
        description (str): 영상 설명
        tags (list, optional): 태그 리스트. Defaults to None.
        privacy (str, optional): 공개 범위 (public/unlisted/private). Defaults to "unlisted".

    Returns:
        dict: YouTube API 응답 (video_id, url 등 포함)
    """
    try:
        # YouTube 인증
        youtube = youtube_authenticate()

        print(f"  📤 업로드 중: {video_path}")

        # 업로드 요청 생성
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags if tags else [],
                    "categoryId": "22",  # People & Blogs (기본값)
                },
                "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
            },
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True),
        )

        # 업로드 실행
        response = request.execute()

        video_id = response["id"]
        video_url = f"https://youtu.be/{video_id}"

        print(f"  ✅ YouTube 업로드 완료!")
        print(f"     Video ID: {video_id}")
        print(f"     URL: {video_url}")

        return {
            "success": True,
            "video_id": video_id,
            "url": video_url,
            "response": response,
        }

    except Exception as e:
        print(f"  ❌ YouTube 업로드 실패: {str(e)}")
        return {"success": False, "error": str(e)}


# def upload_multiple_videos(video_list):
#     """
#     여러 영상을 YouTube에 일괄 업로드

#     Args:
#         video_list (list): 영상 정보가 담긴 딕셔너리 리스트
#                           각 딕셔너리는 video_path, title, description, tags, privacy 키를 포함

#     Returns:
#         list: 각 업로드 결과 리스트
#     """
#     results = []

#     for i, video_info in enumerate(video_list, 1):
#         print(f"\n[{i}/{len(video_list)}] 영상 업로드 시작")

#         result = upload_video_to_youtube(
#             video_path=video_info.get("video_path"),
#             title=video_info.get("title", "Untitled Video"),
#             description=video_info.get("description", ""),
#             tags=video_info.get("tags", []),
#             privacy=video_info.get("privacy", "unlisted"),
#         )

#         results.append(result)

#     # 결과 요약
#     success_count = sum(1 for r in results if r.get("success"))
#     print(f"\n📊 업로드 완료: 성공 {success_count}/{len(video_list)}")

#     return results


# # 테스트용 실행 코드
# if __name__ == "__main__":
#     # 단일 영상 업로드 테스트
#     result = upload_video_to_youtube(
#         video_path="reels.mp4",
#         title="자동 업로드 테스트 🎬",
#         description="API로 자동 업로드한 테스트 영상입니다.",
#         tags=["auto", "upload", "test"],
#         privacy="unlisted",
#     )

#     print("\n업로드 결과:", result)
