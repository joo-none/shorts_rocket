#!/usr/bin/env python3
"""
Shorts Rocket - 금융 뉴스 자동화 쇼츠 생성기
investing.com 크롤링 → 영상 생성 프롬프트 → 영상 생성 → 유튜브 업로드 자동화
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Optional, List

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler import InvestingCrawler, NewsArticle
from src.prompt_generator import VideoPromptGenerator, CharacterType, VideoPrompt
from src.video_generator import (
    VideoGenerator,
    VideoGenerationRequest,
    VideoModel,
    VideoGeneratorFactory,
)
from src.uploader import YouTubeUploader, create_financial_video_info


class ShortsRocket:
    def __init__(self, config_path: str = "config/config.json"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._setup_directories()

        # 모듈 초기화
        self.crawler = InvestingCrawler(
            headless=self.config["crawler"]["investing_com"]["headless"]
        )
        self.prompt_generator = VideoPromptGenerator()
        self.video_generator = VideoGenerator(self.config["video_generation"])
        self.youtube_uploader = YouTubeUploader(
            self.config["youtube"]["credentials_path"]
        )

        self.current_character_index = 0

    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _setup_logging(self):
        """로깅 설정"""
        log_config = self.config["logging"]
        os.makedirs(os.path.dirname(log_config["file"]), exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, log_config["level"]),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_config["file"], encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )

    def _setup_directories(self):
        """필요한 디렉토리 생성"""
        for path in self.config["data_paths"].values():
            os.makedirs(path, exist_ok=True)

    def _get_next_character(self) -> CharacterType:
        """다음 캐릭터 선택 (로테이션 또는 기본값)"""
        if self.config["characters"]["rotation_enabled"]:
            available_chars = self.config["characters"]["available"]
            char_name = available_chars[
                self.current_character_index % len(available_chars)
            ]
            self.current_character_index += 1
        else:
            char_name = self.config["characters"]["default"]

        # 문자열을 CharacterType으로 변환
        char_mapping = {
            "elon_musk": CharacterType.ELON_MUSK,
            "jerome_powell": CharacterType.JEROME_POWELL,
            "jaehoon": CharacterType.JAEHOON,
            "penguin": CharacterType.PENGUIN,
        }

        return char_mapping.get(char_name, CharacterType.ELON_MUSK)

    def crawl_news(self, limit: int = None) -> List[NewsArticle]:
        """뉴스 크롤링"""
        if limit is None:
            limit = self.config["crawler"]["investing_com"]["max_articles"]

        logging.info(f"Starting news crawling (limit: {limit})")
        articles = self.crawler.get_latest_news(limit=limit)

        if articles:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = (
                f"{self.config['data_paths']['crawled']}/articles_{timestamp}.json"
            )
            self.crawler.save_articles(articles, filename)
            logging.info(f"Crawled {len(articles)} articles")
        else:
            logging.warning("No articles crawled")

        return articles

    def generate_video_prompt(
        self, article: NewsArticle, character: CharacterType = None
    ) -> VideoPrompt:
        """영상 생성 프롬프트 생성"""
        if character is None:
            character = self._get_next_character()

        logging.info(f"Generating video prompt with character: {character.value}")

        news_data = {
            "title": article.title,
            "content": article.content,
            "url": article.url,
            "published_date": article.published_date,
            "image_url": article.image_url,
        }

        prompt = self.prompt_generator.generate_prompt(news_data, character)

        # 프롬프트 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config['data_paths']['prompts']}/prompt_{character.value}_{timestamp}.json"
        self.prompt_generator.save_prompt(prompt, filename)

        return prompt

    def generate_video(
        self, prompt: VideoPrompt, model: VideoModel = None
    ) -> Optional[str]:
        """영상 생성"""
        if model is None:
            model_name = self.config["video_generation"]["preferred_model"]
            model = VideoModel.VEO3 if model_name == "veo3" else VideoModel.SORA2

        logging.info(f"Generating video with model: {model.value}")

        request = VideoGenerationRequest(
            prompt=prompt.script,
            visual_description=prompt.visual_description,
            duration=prompt.duration,
            style=prompt.style,
            model=model,
        )

        result = self.video_generator.generate_video(request)

        if result:
            # 비디오 메타데이터 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            metadata_filename = (
                f"{self.config['data_paths']['metadata']}/video_{timestamp}.json"
            )
            self.video_generator.save_video_metadata(result, metadata_filename)

            logging.info(f"Video generated successfully: {result.video_path}")
            return result.video_path
        else:
            logging.error("Video generation failed")
            return None

    def upload_to_youtube(self, video_path: str, prompt: VideoPrompt) -> bool:
        """유튜브 업로드"""
        logging.info(f"Uploading video to YouTube: {video_path}")

        # YouTube 비디오 정보 생성
        character_name = prompt.character.value.replace("_", " ").title()
        youtube_video = create_financial_video_info(
            title=prompt.title,
            content=(
                prompt.script[:500] + "..."
                if len(prompt.script) > 500
                else prompt.script
            ),
            character=character_name,
        )

        # 썸네일 경로 (있는 경우)
        thumbnail_path = video_path.replace(".mp4", "_thumbnail.jpg")
        if not os.path.exists(thumbnail_path):
            thumbnail_path = None

        result = self.youtube_uploader.upload_video(
            video_path=video_path,
            video_info=youtube_video,
            thumbnail_path=thumbnail_path,
        )

        if result.success:
            logging.info(f"Video uploaded successfully: {result.video_url}")

            # 업로드 결과 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = (
                f"{self.config['data_paths']['metadata']}/upload_{timestamp}.json"
            )
            with open(result_filename, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "video_id": result.video_id,
                        "video_url": result.video_url,
                        "title": prompt.title,
                        "character": prompt.character.value,
                        "uploaded_at": result.uploaded_at,
                        "video_path": video_path,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            return True
        else:
            logging.error(f"Upload failed: {result.error_message}")
            return False

    def run_full_pipeline(
        self, article_limit: int = 1, character: CharacterType = None
    ) -> List[str]:
        """전체 파이프라인 실행"""
        results = []

        try:
            # 1. 뉴스 크롤링
            articles = self.crawl_news(limit=article_limit)
            if not articles:
                logging.error("No articles to process")
                return results

            # 2. 각 기사에 대해 영상 생성 및 업로드
            for i, article in enumerate(articles):
                logging.info(
                    f"Processing article {i+1}/{len(articles)}: {article.title}"
                )

                try:
                    # 프롬프트 생성
                    prompt = self.generate_video_prompt(article, character)

                    # 영상 생성
                    video_path = self.generate_video(prompt)
                    if not video_path:
                        logging.error(
                            f"Skipping article {i+1} due to video generation failure"
                        )
                        continue

                    # 유튜브 업로드
                    if self.upload_to_youtube(video_path, prompt):
                        results.append(video_path)

                except Exception as e:
                    logging.error(f"Error processing article {i+1}: {e}")
                    continue

            logging.info(
                f"Pipeline completed. Successfully processed {len(results)} articles"
            )
            return results

        except Exception as e:
            logging.error(f"Pipeline failed: {e}")
            return results
        finally:
            # 크롤러 정리
            self.crawler.close()

    def run_single_step(self, step: str, **kwargs):
        """단일 단계 실행"""
        if step == "crawl":
            return self.crawl_news(kwargs.get("limit", 5))
        elif step == "prompt":
            # 저장된 기사에서 프롬프트 생성
            pass  # TODO: 구현
        elif step == "video":
            # 저장된 프롬프트에서 영상 생성
            pass  # TODO: 구현
        elif step == "upload":
            # 저장된 영상을 업로드
            pass  # TODO: 구현
        else:
            raise ValueError(f"Unknown step: {step}")


def main():
    parser = argparse.ArgumentParser(
        description="Shorts Rocket - 금융 뉴스 자동화 쇼츠 생성기"
    )
    parser.add_argument("--config", default="config/config.json", help="설정 파일 경로")
    parser.add_argument(
        "--step",
        choices=["all", "crawl", "prompt", "video", "upload"],
        default="all",
        help="실행할 단계",
    )
    parser.add_argument("--limit", type=int, default=1, help="처리할 기사 수")
    parser.add_argument(
        "--character",
        choices=["elon_musk", "jerome_powell", "jaehoon", "penguin"],
        help="사용할 캐릭터 (지정하지 않으면 로테이션)",
    )

    args = parser.parse_args()

    try:
        # ShortsRocket 초기화
        rocket = ShortsRocket(args.config)

        # 캐릭터 변환
        character = None
        if args.character:
            char_mapping = {
                "elon_musk": CharacterType.ELON_MUSK,
                "jerome_powell": CharacterType.JEROME_POWELL,
                "jaehoon": CharacterType.JAEHOON,
                "penguin": CharacterType.PENGUIN,
            }
            character = char_mapping[args.character]

        # 단계별 실행
        if args.step == "all":
            results = rocket.run_full_pipeline(args.limit, character)
            print(f"\n✅ 파이프라인 완료! {len(results)}개 영상 처리됨")
        else:
            result = rocket.run_single_step(
                args.step, limit=args.limit, character=character
            )
            print(f"\n✅ {args.step} 단계 완료!")

    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        logging.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
