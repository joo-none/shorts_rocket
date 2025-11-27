#!/usr/bin/env python3
"""
Shorts Rocket - 금융 뉴스 자동화 쇼츠 생성기
investing.com 크롤링 → 영상 생성 프롬프트 → 영상 생성 → 유튜브 업로드 자동화
"""
from dataclasses import dataclass
import os
import sys
import json
import logging
from typing import List

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler import YahooFinanceCrawler, yahoo_crawl_all
from src.prompt_generator import VideoPromptGenerator, CharacterType
from src.video_generator.video_generator import VeoGenerator
from src.video_generator.editor import AutoEditor
from src.uploader.youtube_upload_for_main import upload_video_to_youtube


@dataclass
class NewsArticle:
    """뉴스 기사 데이터 클래스"""
    ticker: str
    title: str
    body: str
    url: str
    images: List[dict]
    time_ago: str
    
def crawl_data(tickers: List[dict] = None, limit: int = 3) -> List[NewsArticle]:
    """
    Yahoo Finance 뉴스 크롤링
    
    Args:
        tickers: [{"name": "TSLA", "count": 2}, {"name": "NVDA", "count": 3}]
        limit: tickers가 없을 때 기본 티커당 기사 수
    
    Returns:
        List[NewsArticle]
    """
    # 기본 티커 설정
    if tickers is None:
        tickers = [
            {"name": "TSLA", "count": limit},
            {"name": "NVDA", "count": limit},
        ]
    
    # 크롤링 실행
    raw_results = yahoo_crawl_all(tickers)
    
    # dict -> NewsArticle 변환
    articles = [
        NewsArticle(
            ticker=r["ticker"],
            title=r["title"],
            body=r["body"],
            url=r["url"],
            images=r["images"],
            time_ago=r["time_ago"]
        )
        for r in raw_results
    ]
    
    return articles


def generate_video_prompt(crawled_data: List[NewsArticle]) -> tuple:
    """크롤링한 기사 바탕으로 주제 선정 및 전체 영상/개별 영상 시나리오 생성"""
    # 주제 선정 및 시나리오 생성 구현

    total_scenario = None  # 전체 영상 시나리오
    individual_scenarios_list = []  # 개별 영상 시나리오 리스트

    return total_scenario, individual_scenarios_list


def generate_video(total_scenario, individual_scenarios_list) -> str:  # 건희 구현
    """
    각 시나리오별 영상 생성 (영상 이어 붙이기)
    :param total_scenario: 전체 프로젝트 이름 또는 주제 (폴더명으로 사용)
    :param individual_scenarios_list: 시나리오 정보가 담긴 딕셔너리 리스트
           예: [{'prompt': 'A cat walking', 'scene_id': 1}, ...]
    :return: 최종 생성된 영상의 파일 경로 (str)
    """

    print(f"\n🚀 프로젝트 시작: {total_scenario}")
    print(f"총 {len(individual_scenarios_list)}개의 씬을 생성하고 병합합니다.")

    # 1. 저장할 폴더명 설정 (공백 제거 등 안전하게 처리)
    # 예: "My Movie" -> "My_Movie"
    project_folder = total_scenario.replace(" ", "_")
    final_output_path = os.path.join(project_folder, "final_movie.mp4")

    # ---------------------------------------------------------
    # 단계 1: Veo를 이용한 영상 일괄 생성 (Batch)
    # ---------------------------------------------------------
    try:
        veo = VeoGenerator()

        # VeoGenerator의 generate_batch 형식에 맞게 데이터 변환
        batch_tasks = []
        for i, scene in enumerate(individual_scenarios_list):
            # 시나리오 리스트에서 프롬프트 추출 (키 이름은 실제 데이터에 맞춰 수정 필요)
            # 예: scene['description'] 혹은 scene['prompt']
            prompt_text = scene.get("prompt") or scene.get("description", "")

            if not prompt_text:
                print(f"⚠️ 경고: {i}번 씬의 프롬프트가 비어있어 건너뜁니다.")
                continue

            task = {
                "prompt": prompt_text
                # # 파일명 자동 지정: scene_001.mp4, scene_002.mp4 ...
                # "output_path": f"scene_{i+1:03d}.mp4",
                # "aspect_ratio": "16:9" # 필요시 설정
            }
            batch_tasks.append(task)

        # 실제 생성 요청 (폴더가 없으면 자동 생성됨)
        if batch_tasks:
            print("🎥 영상 생성 프로세스 진입...")
            veo.generate_batch(task_list=batch_tasks, folder_name=project_folder)
        else:
            raise ValueError("생성할 시나리오가 없습니다.")

    except Exception as e:
        print(f"❌ 영상 생성 중 치명적 오류: {e}")
        return None

    # ---------------------------------------------------------
    # 단계 2: AutoEditor를 이용한 영상 병합
    # ---------------------------------------------------------
    try:
        print("🎞️ 영상 편집 및 병합 프로세스 진입...")

        editor = AutoEditor(output_resolution=(1920, 1080))

        # 생성된 폴더에서 영상 로드
        editor.load_clips_from_folder(project_folder)

        # 이어 붙이기
        editor.concatenate()

        # if 'bgm_path' in total_scenario: ...

        # 최종 내보내기
        editor.export(final_output_path)

        print(f"🎉 모든 작업 완료! 결과물: {final_output_path}")
        return final_output_path

    except Exception as e:
        print(f"❌ 영상 편집 중 오류: {e}")
        return None


# # --- 테스트 실행용 ---
# if __name__ == "__main__":
#     # 가상의 입력 데이터
#     title = "Cyberpunk_Story"
#     scenarios = [
#         {"prompt": "A futuristic city skyline with neon lights, cinematic shot"},
#         {"prompt": "A robot walking in the rain, close up"},
#         {"prompt": "The robot looks at a glowing holographic sign"}
#     ]

#     result_path = generate_video(title, scenarios)
#     print(f"반환된 경로: {result_path}")


from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# YouTube API 인증 범위
YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"] #강산 구현


def youtube_authenticate():
    """
    YouTube API 인증 및 서비스 객체 반환
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
            flow = InstalledAppFlow.from_client_secrets_file("credentials_youtube.json", YT_SCOPES)
            creds = flow.run_local_server(port=8080)

        # 토큰 저장
        with open("token_youtube.json", "w") as token:
            token.write(creds.to_json())
        print("  ✅ YouTube 토큰 저장 완료!")

    return build("youtube", "v3", credentials=creds)


def upload_video_to_youtube(video_path, title, description, tags=None, privacy="unlisted"):
    """
    YouTube에 영상 업로드

    Returns:
        dict: {'success': bool, 'video_id': str, 'url': str, ...}
    """
    try:
        youtube = youtube_authenticate()

        print(f"  업로드 중: {video_path}")

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags if tags else [],
                    "categoryId": "22"
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False
                }
            },
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
        )

        response = request.execute()

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}" if video_id else None

        print(f"  YouTube 업로드 완료! URL: {video_url}")

        return {"success": True, "video_id": video_id, "url": video_url, "response": response}

    except Exception as e:
        print(f"  YouTube 업로드 실패: {e}")
        return {"success": False, "error": str(e)}


def upload_multiple_videos(video_list):
    """
    여러 영상을 YouTube에 일괄 업로드
    video_list: [{'video_path':..., 'title':..., 'description':..., 'tags':..., 'privacy':...}, ...]
    """
    results = []
    for i, video_info in enumerate(video_list, 1):
        print(f"\n[{i}/{len(video_list)}] 영상 업로드 시작")
        res = upload_video_to_youtube(
            video_path=video_info.get("video_path"),
            title=video_info.get("title", "Untitled Video"),
            description=video_info.get("description", ""),
            tags=video_info.get("tags", []),
            privacy=video_info.get("privacy", "unlisted"),
        )
        results.append(res)

    success_count = sum(1 for r in results if r.get("success"))
    print(f"\n📊 업로드 완료: 성공 {success_count}/{len(video_list)}")
    return results


def upload_to_youtube(main_video: str) -> bool:
    """유튜브 업로드"""
    # 남은 작업
    # - 영상 제목 title
    # - description
    # - tags
    try:

        # title =
        # description =
        # tags =

        result = upload_video_to_youtube(
            video_path=main_video,
            title="금융 쇼츠 영상",
            description="금융 뉴스를 바탕으로 자동 생성된 쇼츠 영상입니다.",
            tags=["finance", "news", "shorts", "금융", "뉴스"],
            privacy="public",
        )

        return result.get("success", False)

    except Exception as e:
        print(f"업로드 실패: {e}")
        return False


def main():

    # 1. 기사 크롤링
    crawled_data = crawl_data()

    # 2. 크롤링한 기사 바탕으로 주제 선정 및 전체 영상/개별 영상 시나리오 생성
    total_scenario, individual_scenarios_list = generate_video_prompt(crawled_data)

    # 3. 각 시나리오별 영상 생성 (영상 이어 붙이기)
    main_video = generate_video(total_scenario, individual_scenarios_list)

    # 4. 업로드
    upload_to_youtube(main_video)


if __name__ == "__main__":
    main()
