import os
import requests
from datetime import datetime

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")

def post_to_instagram(image_url, caption):
    """인스타그램에 포스팅"""
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_USER_ID:
        print("인스타그램 토큰이 설정되지 않았습니다.")
        return False

    # 1단계: 미디어 컨테이너 생성
    create_url = f"https://graph.instagram.com/v18.0/{INSTAGRAM_USER_ID}/media"
    create_data = {
        "image_url": image_url,
        "caption":   caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    res = requests.post(create_url, data=create_data)
    result = res.json()

    if "id" not in result:
        print(f"미디어 생성 실패: {result}")
        return False

    container_id = result["id"]
    print(f"미디어 컨테이너 생성 완료: {container_id}")

    # 2단계: 포스팅 발행
    publish_url = f"https://graph.instagram.com/v18.0/{INSTAGRAM_USER_ID}/media_publish"
    publish_data = {
        "creation_id":  container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    res = requests.post(publish_url, data=publish_data)
    result = res.json()

    if "id" in result:
        print(f"포스팅 완료! Post ID: {result['id']}")
        return True
    else:
        print(f"포스팅 실패: {result}")
        return False

def generate_caption(summary, market_data=None):
    """캡션 생성"""
    today = datetime.now().strftime("%Y년 %m월 %d일")
    caption = f"""📒 오늘의 경제 노트 | {today}

{summary}

"""
    if market_data:
        caption += "📊 주요 시세\n"
        for name, info in market_data.items():
            arrow = "▲" if info["change"] >= 0 else "▼"
            caption += f"{name}: {info['price']:,} {arrow} {abs(info['change_pct'])}%\n"

    caption += """
#오늘의경제노트 #경제 #주식 #부동산 #경제뉴스 #주식뉴스 #재테크 #경제공부"""
    return caption

if __name__ == "__main__":
    # 테스트용
    test_caption = generate_caption("오늘의 경제 동향 테스트입니다.")
    print(test_caption)