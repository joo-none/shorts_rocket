# main 페이지
"""
쇼츠 자동 생성 파이프라인 (Main Controller)
작성자: 준언
설명: 전체 파이프라인의 흐름을 관리하는 메인 코드
"""

import os
from datetime import datetime

# -----------------------------
# 1. 데이터 수집 모듈 (재훈)
# -----------------------------
def collect_data():
    """
    뉴스/기사/이미지 데이터 수집
    - 야후파이낸스 / investing.com 크롤링
    - Tesla, NVIDIA 관련 기사 수집
    - 기사 이미지도 함께 저장
    """
    print("[1] 데이터 수집 중...")
    # 예시: 실제 구현은 재훈 담당
    # articles = crawl_yahoo_finance("Tesla")
    # images = download_images(articles)
    articles = [{"title": "Tesla stock surges", "content": "Tesla shares rose 10%..."}]
    print(f"  > {len(articles)}개 기사 수집 완료")
    return articles


# -----------------------------
# 2. 프롬프트 생성 모듈 (준언, 강산)
# -----------------------------
def generate_prompts(articles):
    """
    영상/이미지 생성을 위한 프롬프트 생성
    - 제목, 캡션, 해시태그, 자막, 이미지 프롬프트 등
    """
    print("[2] 프롬프트 생성 중...")
    prompts = []
    for article in articles:
        prompt = {
            "title": f"{article['title']} - AI Generated",
            "caption": "테슬라 주가 급등 이유를 알아봅시다!",
            "hashtags": ["#Tesla", "#AI", "#Finance"],
            "image_prompt": f"Tesla stock market news illustration",
            "script": f"오늘은 {article['title']} 소식을 전해드릴게요."
        }
        prompts.append(prompt)
    print(f"  > {len(prompts)}개 프롬프트 생성 완료")
    return prompts


# -----------------------------
# 3. 영상/사진 생성 모듈 (건희)
# -----------------------------
def generate_media(prompts):
    """
    프롬프트를 기반으로 영상/이미지 생성
    - MoviePy, Vrew, Veo 등 활용
    - OpenAI API로 음성 변환 가능
    """
    print("[3] 영상/사진 생성 중...")
    generated_files = []
    for p in prompts:
        # 예시: 실제 구현은 건희 담당
        filename = f"output_{p['title'].replace(' ', '_')}.mp4"
        # create_video(p['script'], p['image_prompt'])
        generated_files.append(filename)
    print(f"  > {len(generated_files)}개 영상 생성 완료")
    return generated_files


# -----------------------------
# 4. 드라이브 저장 모듈 (건희)
# -----------------------------
def save_to_drive(files):
    """
    생성된 영상/이미지를 구글 드라이브에 업로드
    """
    print("[4] 구글 드라이브에 저장 중...")
    for f in files:
        # upload_to_drive(f)
        print(f"  > {f} 업로드 완료")
    print("  > 모든 파일 저장 완료")


# -----------------------------
# 5. 업로드 모듈 (강산)
# -----------------------------
def upload_to_platform(files):
    """
    인스타그램 또는 유튜브에 업로드
    - 인스타 API / 유튜브 API 활용
    - DB 연동 필요 시 구글 드라이브 링크 사용
    """
    print("[5] 플랫폼 업로드 중...")
    for f in files:
        # upload_to_instagram(f)
        # 또는 upload_to_youtube(f)
        print(f"  > {f} 업로드 완료 (예시)")
    print("  > 모든 업로드 완료")


# -----------------------------
# 메인 파이프라인 실행
# -----------------------------
def main():
    print("=== 쇼츠 자동 생성 파이프라인 시작 ===")
    start_time = datetime.now()

    # 1. 데이터 수집
    articles = collect_data()

    # 2. 프롬프트 생성
    prompts = generate_prompts(articles)

    # 3. 영상/사진 생성
    generated_files = generate_media(prompts)

    # 4. 드라이브 저장
    save_to_drive(generated_files)

    # 5. 업로드
    upload_to_platform(generated_files)

    end_time = datetime.now()
    print(f"=== 파이프라인 완료 ({(end_time - start_time).seconds}초 소요) ===")


if __name__ == "__main__":
    main()