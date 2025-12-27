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
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

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
            time_ago=r["time_ago"],
        )
        for r in raw_results
    ]

    return articles


# def generate_video_prompt(crawled_data: List[NewsArticle]) -> tuple:
#     """크롤링한 기사 바탕으로 주제 선정 및 전체 영상/개별 영상 시나리오 생성"""
#     # 주제 선정 및 시나리오 생성 구현

#     total_scenario = None  # 전체 영상 시나리오
#     individual_scenarios_list = []  # 개별 영상 시나리오 리스트

#     return total_scenario, individual_scenarios_list

def generate_video_prompt(crawled_data: List[NewsArticle]) -> tuple:
    """
    테스트를 위한 임시 시나리오 생성 함수.
    crawled_data의 내용을 일부 반영하여 VeoGenerator가 인식할 수 있는 포맷으로 반환합니다.
    """
    print(f"\n📝 [Prompt Generation] {len(crawled_data)}개의 기사를 바탕으로 시나리오 생성 중...")

    # 1. 전체 영상 컨셉 (현재는 로그용)
    total_scenario = "최신 금융 뉴스 요약 쇼츠"

    # 2. 개별 영상 클립 시나리오 (VeoGenerator.run_batch에서 사용될 형식)
    # 기사 데이터를 기반으로 2~3개의 클립만 테스트용으로 생성
    individual_scenarios_list = []
    
    # 예시로 최대 2개의 기사만 사용하여 테스트
    test_articles = crawled_data[:2] if crawled_data else []

    for i, article in enumerate(test_articles):
        # 기사 제목이나 내용을 바탕으로 프롬프트 구성
        # 팁: Veo는 구체적인 시각적 묘사가 있을 때 결과가 더 좋습니다.
        visual_prompt = f"Cinematic digital art of {article.ticker} stock symbol glowing on a high-tech screen, 4k, professional financial news style."
        
        clip_task = {
            "prompt": visual_prompt,
            "gen_image_first": True,       # Imagen으로 첫 프레임 생성 후 영상 제작 (안정적임)
            "image_prompt": visual_prompt, # 이미지 생성에 사용될 프롬프트
            "aspect_ratio": "9:16"         # 쇼츠용 세로 비율
        }
        individual_scenarios_list.append(clip_task)

    # 기사가 없을 경우를 대비한 기본 더미 데이터
    if not individual_scenarios_list:
        individual_scenarios_list = [
            {
                "prompt": "A futuristic digital world map showing stock market data flow, neon blue and gold, 4k, vertical.",
                "gen_image_first": True,
                "aspect_ratio": "9:16"
            }
        ]

    print(f"✅ 총 {len(individual_scenarios_list)}개의 클립 시나리오가 준비되었습니다.")
    return total_scenario, individual_scenarios_list


def generate_video(total_scenario: str, individual_scenarios_list: List[dict[str, any]]) -> str:
    """
    생성된 시나리오를 바탕으로 VeoGenerator를 통해 숏폼 영상을 생성하고,
    AutoEditor를 통해 하나로 합칩니다.

    Args:
        total_scenario: 전체 영상 컨셉 (현재 미사용)
        individual_scenarios_list: 개별 영상 프롬프트 리스트 [{"prompt": "..."}, ...]

    Returns:
        str: 최종 생성된 영상 파일 경로
    """
    print("\n=== [Video Generation Start] ===")
    
    # 1. 설정 정의
    API_KEY = os.getenv("GOOGLE_API_KEYLJE") # 환경변수에서 키 가져오기
    if not API_KEY:
        raise ValueError("❌ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        
    TEMP_CLIPS_FOLDER = "temp_shorts_clips"
    FINAL_OUTPUT_PATH = "final_shorts_output.mp4"

    # 2. VeoGenerator 초기화 및 일괄 생성
    try:
        generator = VeoGenerator(api_key=API_KEY, model_name="veo-3.1-generate-preview")
        
        # individual_scenarios_list가 VeoGenerator가 요구하는 tasks 형식과 일치한다고 가정
        # (즉, [{'prompt': '...'}, ... ] 형태)
        print(f"총 {len(individual_scenarios_list)}개의 클립 생성을 시작합니다.")
        generator.run_batch(individual_scenarios_list, output_folder=TEMP_CLIPS_FOLDER)
        
    except Exception as e:
        print(f"❌ 영상 생성 중 오류 발생: {e}")
        # 생성 단계에서 실패하면 더 이상 진행하지 않음
        raise e

    # 3. AutoEditor 초기화 및 병합
    print("\n=== [Video Editing Start] ===")
    try:
        editor = AutoEditor(resolution=(1080, 1920)) # 쇼츠용 세로 해상도 (선택사항)
        
        # 메서드 체이닝으로 로드 -> 병합 -> 내보내기 수행
        (editor.load_from_folder(TEMP_CLIPS_FOLDER)
               .concatenate()
               # 필요하다면 여기에 BGM, 자막 추가 로직 구현
               # .add_bgm("background_music.mp3", volume=0.2)
               .export(FINAL_OUTPUT_PATH))
               
        if os.path.exists(FINAL_OUTPUT_PATH):
            print(f"✅ 최종 영상 생성 완료: {FINAL_OUTPUT_PATH}")
            return FINAL_OUTPUT_PATH
        else:
            raise FileNotFoundError("최종 영상 파일 생성에 실패했습니다.")

    except Exception as e:
        print(f"❌ 영상 편집 중 오류 발생: {e}")
        raise e


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
