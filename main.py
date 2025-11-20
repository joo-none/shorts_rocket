#!/usr/bin/env python3
"""
Shorts Rocket - 금융 뉴스 자동화 쇼츠 생성기
investing.com 크롤링 → 영상 생성 프롬프트 → 영상 생성 → 유튜브 업로드 자동화
"""

import os
import sys
import json
import logging
from typing import List

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler import InvestingCrawler, NewsArticle
from src.prompt_generator import VideoPromptGenerator, CharacterType
from src.video_generator import VideoGenerator
from src.uploader.youtube_upload_for_main import upload_video_to_youtube


def crawl_data(limit: int = None) -> List[NewsArticle]:
    """뉴스 크롤링"""
    # 기사 크롤링 구현
    pass


def generate_video_prompt(crawled_data: List[NewsArticle]) -> tuple:
    """크롤링한 기사 바탕으로 주제 선정 및 전체 영상/개별 영상 시나리오 생성"""
    # 주제 선정 및 시나리오 생성 구현

    total_scenario = None  # 전체 영상 시나리오
    individual_scenarios_list = []  # 개별 영상 시나리오 리스트

    return total_scenario, individual_scenarios_list


def generate_video(total_scenario, individual_scenarios_list) -> str:  # 건희 구현
    """각 시나리오별 영상 생성 (영상 이어 붙이기)"""
    # 시나리오별 영상 생성 및 결합 구현
    main_video = None

    return main_video


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
