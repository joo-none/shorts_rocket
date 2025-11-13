from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import logging
from datetime import datetime


class CharacterType(Enum):
    ELON_MUSK = "elon_musk"
    JEROME_POWELL = "jerome_powell"
    JAEHOON = "jaehoon"
    PENGUIN = "penguin"


@dataclass
class VideoPrompt:
    character: CharacterType
    title: str
    script: str
    visual_description: str
    duration: int  # seconds
    style: str
    created_at: str


class VideoPromptGenerator:
    def __init__(self):
        self.character_templates = self._load_character_templates()

    def _load_character_templates(self) -> Dict[CharacterType, Dict]:
        """캐릭터별 프롬프트 템플릿 로드"""
        return {
            CharacterType.ELON_MUSK: {
                "persona": "일론 머스크의 톤과 스타일로 설명하는 혁신적이고 미래지향적인 관점",
                "visual_style": "미래적이고 기술적인 배경, 스페이스X 로켓이나 테슬라 차량이 있는 환경",
                "speech_pattern": "혁신, 미래, 기술에 대한 열정적인 언어 사용",
                "outfit": "검은색 티셔츠 또는 정장, 캐주얼하면서도 전문적인 모습",
            },
            CharacterType.JEROME_POWELL: {
                "persona": "연방준비제도 의장으로서 신중하고 전문적인 경제 분석",
                "visual_style": "연방준비제도 건물이나 경제 차트가 있는 전문적인 배경",
                "speech_pattern": "신중하고 분석적인 경제 용어 사용",
                "outfit": "정장, 넥타이, 전문적이고 권위있는 모습",
            },
            CharacterType.JAEHOON: {
                "persona": "친근하고 이해하기 쉽게 설명하는 금융 전문가",
                "visual_style": "현대적이고 깔끔한 스튜디오나 사무실 환경",
                "speech_pattern": "친근하면서도 전문적인 설명, 일반인도 이해할 수 있는 언어",
                "outfit": "비즈니스 캐주얼, 접근하기 쉬운 모습",
            },
            CharacterType.PENGUIN: {
                "persona": "귀엽고 재미있는 펭귄이 알려주는 금융 뉴스",
                "visual_style": "남극 빙하나 귀여운 애니메이션 배경",
                "speech_pattern": "귀엽고 재미있는 표현, 이해하기 쉬운 설명",
                "outfit": "펭귄 모습, 때로는 작은 액세서리 착용",
            },
        }

    def generate_prompt(
        self, news_data: Dict, character: CharacterType, duration: int = 60
    ) -> VideoPrompt:
        """뉴스 데이터를 바탕으로 영상 생성 프롬프트 생성"""

        title = self._generate_title(news_data, character)
        script = self._generate_script(news_data, character)
        visual_description = self._generate_visual_description(news_data, character)
        style = self._get_video_style(character)

        return VideoPrompt(
            character=character,
            title=title,
            script=script,
            visual_description=visual_description,
            duration=duration,
            style=style,
            created_at=datetime.now().isoformat(),
        )

    def _generate_title(self, news_data: Dict, character: CharacterType) -> str:
        """영상 제목 생성"""
        original_title = news_data.get("title", "")

        title_templates = {
            CharacterType.ELON_MUSK: f"🚀 일론 머스크가 알려주는: {original_title}",
            CharacterType.JEROME_POWELL: f"📊 제롬 파월이 분석하는: {original_title}",
            CharacterType.JAEHOON: f"💡 재훈이가 쉽게 설명하는: {original_title}",
            CharacterType.PENGUIN: f"🐧 펭귄이 알려주는 금융뉴스: {original_title}",
        }

        return title_templates[character]

    def _generate_script(self, news_data: Dict, character: CharacterType) -> str:
        """영상 스크립트 생성"""
        content = news_data.get("content", "")
        template = self.character_templates[character]

        base_script = f"""
        [인트로]
        안녕하세요! {self._get_character_greeting(character)}
        
        오늘은 중요한 금융 뉴스를 가져왔습니다.
        
        [메인 콘텐츠]
        {self._format_content_for_character(content, character)}
        
        [아웃트로]
        {self._get_character_outro(character)}
        """

        return base_script.strip()

    def _generate_visual_description(
        self, news_data: Dict, character: CharacterType
    ) -> str:
        """영상 비주얼 설명 생성"""
        template = self.character_templates[character]

        visual_prompt = f"""
        캐릭터: {template['persona']}
        복장: {template['outfit']}
        배경: {template['visual_style']}
        
        영상 스타일:
        - 16:9 비율의 풀HD 영상
        - {character.value} 스타일의 프레젠테이션
        - 부드러운 조명과 전문적인 카메라 앵글
        - 뉴스 내용과 관련된 차트나 이미지 삽입
        - 60초 길이의 쇼츠 형태
        
        시각적 요소:
        - 인트로: 캐릭터 등장과 인사
        - 메인: 뉴스 설명과 분석
        - 아웃트로: 마무리 멘트와 구독 유도
        """

        return visual_prompt.strip()

    def _get_character_greeting(self, character: CharacterType) -> str:
        greetings = {
            CharacterType.ELON_MUSK: "혁신의 아이콘, 일론 머스크입니다.",
            CharacterType.JEROME_POWELL: "연방준비제도 의장 제롬 파월입니다.",
            CharacterType.JAEHOON: "여러분의 금융 가이드, 재훈입니다.",
            CharacterType.PENGUIN: "귀여운 금융 펭귄입니다! 🐧",
        }
        return greetings[character]

    def _get_character_outro(self, character: CharacterType) -> str:
        outros = {
            CharacterType.ELON_MUSK: "미래를 함께 만들어갑시다. 구독과 좋아요 부탁드립니다!",
            CharacterType.JEROME_POWELL: "경제 분석이 도움이 되었기를 바랍니다. 구독해주세요.",
            CharacterType.JAEHOON: "도움이 되셨나요? 구독하고 알림 설정해주세요!",
            CharacterType.PENGUIN: "펭펭! 구독하면 더 많은 금융 뉴스를 알려드려요! 🐧❤️",
        }
        return outros[character]

    def _format_content_for_character(
        self, content: str, character: CharacterType
    ) -> str:
        """캐릭터별로 콘텐츠 포맷팅"""
        if len(content) > 500:
            content = content[:500] + "..."

        if character == CharacterType.ELON_MUSK:
            return f"이 뉴스는 우리의 미래에 중요한 영향을 미칠 것입니다. {content}"
        elif character == CharacterType.JEROME_POWELL:
            return f"경제적 관점에서 분석해보면, {content}"
        elif character == CharacterType.JAEHOON:
            return f"쉽게 설명드리면, {content}"
        elif character == CharacterType.PENGUIN:
            return f"펭펭! 이 소식을 알려드릴게요! {content}"

        return content

    def _get_video_style(self, character: CharacterType) -> str:
        styles = {
            CharacterType.ELON_MUSK: "futuristic_tech_style",
            CharacterType.JEROME_POWELL: "professional_financial_style",
            CharacterType.JAEHOON: "modern_casual_style",
            CharacterType.PENGUIN: "cute_animated_style",
        }
        return styles[character]

    def save_prompt(self, prompt: VideoPrompt, filename: str):
        """생성된 프롬프트를 파일로 저장"""
        prompt_data = {
            "character": prompt.character.value,
            "title": prompt.title,
            "script": prompt.script,
            "visual_description": prompt.visual_description,
            "duration": prompt.duration,
            "style": prompt.style,
            "created_at": prompt.created_at,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)

        logging.info(f"Prompt saved to {filename}")


if __name__ == "__main__":
    # 테스트 예제
    sample_news = {
        "title": "비트코인 가격 급등, 새로운 고점 기록",
        "content": "비트코인이 오늘 새로운 사상 최고가를 기록하며 투자자들의 관심을 끌고 있습니다...",
    }

    generator = VideoPromptGenerator()
    prompt = generator.generate_prompt(sample_news, CharacterType.ELON_MUSK)
    generator.save_prompt(prompt, "data/prompts/test_prompt.json")
    print("프롬프트 생성 완료!")
