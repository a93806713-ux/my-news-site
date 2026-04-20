import time
import os
import requests
import base64
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
IMGBB_API_KEY          = os.environ.get("IMGBB_API_KEY", "")

def create_post_image(summary, market_data=None):
    """포스팅용 이미지 생성"""
    width, height = 1080, 1080
    img  = Image.new("RGB", (width, height), color="#1a1a2e")
    draw = ImageDraw.Draw(img)

    # 배경 그라데이션 효과 (사각형으로 대체)
    for i in range(0, height, 2):
        alpha = int(255 * (1 - i / height) * 0.3)
        draw.rectangle([0, i, width, i+2], fill=(74, 108, 247))

    # 타이틀
    try:
        font_title  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_body   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        font_small  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        font_market = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except:
        font_title  = ImageFont.load_default()
        font_body   = font_title
        font_small  = font_title
        font_market = font_title

    # 날짜
    today = datetime.now().strftime("%Y.%m.%d")
    draw.text((60, 60), today, font=font_small, fill="#aabbcc")

    # 제목
    draw.text((60, 110), "Today's Economy Note", font=font_title, fill="white")
    draw.text((60, 175), "오늘의 경제 노트", font=font_body, fill="#4a6cf7")

    # 구분선
    draw.rectangle([60, 220, 1020, 223], fill="#4a6cf7")

    # AI 요약 텍스트 (줄바꿈 처리)
    y_text = 250
    words  = summary[:200] if summary else "오늘의 경제 동향을 확인하세요."
    lines  = []
    line   = ""
    for char in words:
        line += char
        if len(line) >= 22:
            lines.append(line)
            line = ""
    if line:
        lines.append(line)

    for i, l in enumerate(lines[:6]):
        draw.text((60, y_text + i * 48), l, font=font_body, fill="#e0e8f0")

    # 시세 정보
    if market_data:
        y_market = 580
        draw.rectangle([60, y_market - 10, 1020, y_market - 7], fill="#333355")
        draw.text((60, y_market + 10), "Market", font=font_small, fill="#aabbcc")
        y_market += 55

        items = list(market_data.items())[:4]
        for i, (name, info) in enumerate(items):
            x = 60 + (i % 2) * 480
            y = y_market + (i // 2) * 100
            arrow = "▲" if info["change"] >= 0 else "▼"
            color = "#ff6b6b" if info["change"] >= 0 else "#4ecdc4"
            draw.text((x, y), f"{name}", font=font_small, fill="#aabbcc")
            draw.text((x, y + 34), f"{info['price']:,}", font=font_market, fill="white")
            draw.text((x + 200, y + 40), f"{arrow} {abs(info['change_pct'])}%", font=font_small, fill=color)

    # 하단 로고
    draw.rectangle([0, 980, width, 1080], fill="#111122")
    draw.text((60, 1000), "📒 오늘의 경제 노트  |  hy.econ", font=font_small, fill="#aabbcc")
    draw.text((800, 1000), "#경제 #주식 #재테크", font=font_small, fill="#4a6cf7")

    return img

def upload_to_imgbb(img):
    """이미지를 imgbb에 업로드하고 URL 반환"""
    if not IMGBB_API_KEY:
        print("IMGBB_API_KEY 없음")
        return None

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    res = requests.post(
        "https://api.imgbb.com/1/upload",
        data={
            "key":   IMGBB_API_KEY,
            "image": img_base64,
            "name":  f"economy_note_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        }
    )
    result = res.json()
    if result.get("success"):
        url = result["data"]["url"]
        print(f"이미지 업로드 완료: {url}")
        return url
    else:
        print(f"이미지 업로드 실패: {result}")
        return None

def post_to_instagram(image_url, caption):
    """인스타그램에 포스팅"""
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_USER_ID:
        print("인스타그램 토큰이 설정되지 않았습니다.")
        return False

    # 1단계: 미디어 컨테이너 생성
    create_url  = f"https://graph.instagram.com/v18.0/{INSTAGRAM_USER_ID}/media"
    create_data = {
        "image_url":    image_url,
        "caption":      caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    res    = requests.post(create_url, data=create_data)
    result = res.json()

    if "id" not in result:
        print(f"미디어 생성 실패: {result}")
        return False

    container_id = result["id"]
    print(f"미디어 컨테이너 생성 완료: {container_id}")

    # 2단계: 미디어 처리 대기 (30초)
    print("미디어 처리 대기 중... (30초)")
    time.sleep(30)

    # 3단계: 상태 확인
    status_url = f"https://graph.instagram.com/v18.0/{container_id}"
    status_res = requests.get(status_url, params={
        "fields":       "status_code",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    status = status_res.json()
    print(f"미디어 상태: {status}")

    # 4단계: 포스팅 발행
    publish_url  = f"https://graph.instagram.com/v18.0/{INSTAGRAM_USER_ID}/media_publish"
    publish_data = {
        "creation_id":  container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    res    = requests.post(publish_url, data=publish_data)
    result = res.json()

    if "id" in result:
        print(f"포스팅 완료! Post ID: {result['id']}")
        return True
    else:
        print(f"포스팅 실패: {result}")
        return False

def generate_caption(summary, market_data=None):
    """캡션 생성"""
    today   = datetime.now().strftime("%Y년 %m월 %d일")
    caption = f"""📒 오늘의 경제 노트 | {today}

{summary}

"""
    if market_data:
        caption += "📊 주요 시세\n"
        for name, info in market_data.items():
            arrow   = "▲" if info["change"] >= 0 else "▼"
            caption += f"{name}: {info['price']:,} {arrow} {abs(info['change_pct'])}%\n"

    caption += """
#오늘의경제노트 #경제 #주식 #부동산 #경제뉴스 #주식뉴스 #재테크 #경제공부 #hy_econ"""
    return caption

if __name__ == "__main__":
    print("이미지 생성 테스트...")
    img = create_post_image("오늘의 경제 동향 테스트입니다. AI가 분석한 주요 경제 뉴스를 확인하세요.")
    img.save("test_post.png")
    print("test_post.png 저장 완료!")