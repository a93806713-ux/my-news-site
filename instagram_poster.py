import os
import requests
import base64
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
IMGBB_API_KEY          = os.environ.get("IMGBB_API_KEY", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_font(size, bold=False):
    font_paths = [
        os.path.join(BASE_DIR, "NanumGothicBold.ttf") if bold else os.path.join(BASE_DIR, "NanumGothic.ttf"),
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf" if bold else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def create_post_image(summary, market_data=None):
    width, height = 1080, 1080
    img  = Image.new("RGB", (width, height), color="#0d1117")
    draw = ImageDraw.Draw(img)

    # 배경 장식 원
    draw.ellipse([700, -100, 1200, 400], fill="#1a2744")
    draw.ellipse([-100, 700, 400, 1200], fill="#1a2744")
    draw.ellipse([800, 600, 1150, 950],  fill="#111827")

    # 상단 컬러 바
    draw.rectangle([0, 0, width, 8], fill="#4a6cf7")

    font_huge   = get_font(56, bold=True)
    font_large  = get_font(36, bold=True)
    font_medium = get_font(28)
    font_small  = get_font(22)
    font_tiny   = get_font(18)

    # 날짜
    today = datetime.now().strftime("%Y.%m.%d")
    draw.text((60, 30),  today,                  font=font_tiny,  fill="#5a6a8a")
    draw.text((60, 65),  "오늘의",               font=font_huge,  fill="#ffffff")
    draw.text((60, 130), "경제 노트",            font=font_huge,  fill="#4a6cf7")
    draw.text((60, 200), "Today's Economy Note", font=font_small, fill="#5a6a8a")

    # 구분선
    draw.rectangle([60, 245, 380, 249],  fill="#4a6cf7")
    draw.rectangle([390, 245, 480, 249], fill="#2a3a5a")

    # AI 요약 타이틀
    draw.text((60, 268), "AI 경제 동향 요약", font=font_medium, fill="#a0b0cc")

    # 요약 텍스트 - 마침표 뒤에서 줄바꿈
    y_text = 312
    text   = (summary or "오늘의 경제 동향을 확인하세요.").replace("**", "").replace("##", "").replace("*", "").strip()

    # 마침표 기준으로 문장 분리
    sentences = []
    temp = ""
    for char in text:
        temp += char
        if char in ['.', '!', '?']:
            sentences.append(temp.strip())
            temp = ""
    if temp.strip():
        sentences.append(temp.strip())

    # 문장이 너무 길면 추가 줄바꿈
    lines = []
    for sentence in sentences:
        while True:
            bbox = draw.textbbox((0, 0), sentence, font=font_medium)
            if bbox[2] <= 920:
                lines.append(sentence)
                break
            else:
                mid = len(sentence) // 2
                lines.append(sentence[:mid])
                sentence = sentence[mid:]

    for i, l in enumerate(lines[:8]):
        draw.text((60, y_text + i * 40), l, font=font_medium, fill=(220, 230, 248))

    # 시세 정보 섹션
    if market_data:
        y_market = 660
        draw.rounded_rectangle(
            [40, y_market - 16, width - 40, y_market + 270],
            radius=20, fill="#131c2e"
        )
        draw.text((65, y_market), "주요 시세", font=font_medium, fill="#a0b0cc")
        draw.rectangle([65, y_market + 36, width - 65, y_market + 38], fill="#1e2d4a")
        y_market += 55

        for i, (name, info) in enumerate(list(market_data.items())[:4]):
            col   = i % 2
            row   = i // 2
            x     = 70  + col * 490
            y     = y_market + row * 95
            is_up = info["change"] >= 0
            arrow = "▲" if is_up else "▼"
            color = (255, 100, 100) if is_up else (78, 205, 196)

            price_val = info["price"]
            if price_val > 10000:
                price_str = f"{price_val:,.0f}"
            elif price_val > 100:
                price_str = f"{price_val:,.1f}"
            else:
                price_str = f"{price_val:,.2f}"

            draw.text((x, y),       name,      font=font_small, fill=(140, 160, 190))
            draw.text((x, y + 28),  price_str, font=font_large, fill=(255, 255, 255))
            draw.text((x + 210, y + 36), f"{arrow} {abs(info['change_pct'])}%", font=font_small, fill=color)

    # 하단 바
    draw.rectangle([0, 1018, width, 1022], fill="#4a6cf7")
    draw.rectangle([0, 1022, width, 1080], fill="#0a0f1a")
    draw.text((60,  1038), "오늘의 경제 노트", font=font_small, fill="#4a6cf7")
    draw.text((680, 1038), "@hy.econ",         font=font_small, fill="#5a6a8a")

    return img

def upload_to_imgbb(img):
    if not IMGBB_API_KEY:
        print("IMGBB_API_KEY 없음")
        return None

    buffer     = io.BytesIO()
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
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_USER_ID:
        print("인스타그램 토큰이 설정되지 않았습니다.")
        return False

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

    print("미디어 처리 대기 중... (30초)")
    time.sleep(30)

    status_res = requests.get(
        f"https://graph.instagram.com/v18.0/{container_id}",
        params={"fields": "status_code", "access_token": INSTAGRAM_ACCESS_TOKEN}
    )
    print(f"미디어 상태: {status_res.json()}")

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
    today   = datetime.now().strftime("%Y년 %m월 %d일")
    caption = f"오늘의 경제 노트 | {today}\n\n{summary}\n\n"

    if market_data:
        caption += "주요 시세\n"
        for name, info in market_data.items():
            arrow   = "▲" if info["change"] >= 0 else "▼"
            caption += f"{name}: {info['price']:,} {arrow} {abs(info['change_pct'])}%\n"

    caption += "\n#오늘의경제노트 #경제 #주식 #부동산 #경제뉴스 #재테크 #경제공부 #hy_econ"
    return caption

if __name__ == "__main__":
    market = {
        "코스피":   {"price": 2601.5, "change": 12.3,  "change_pct": 0.47},
        "나스닥":   {"price": 17845.0,"change": -45.2,  "change_pct": -0.25},
        "비트코인": {"price": 84250.0,"change": 1250.0, "change_pct": 1.5},
        "환율":     {"price": 1385.0, "change": -3.5,   "change_pct": -0.25},
    }
    img = create_post_image(
        "코스피가 2600선을 회복했습니다. 외국인 매수세가 강하게 유입되며 반등에 성공했습니다. 환율은 1380원대로 하락했고 비트코인은 강세를 이어가고 있습니다.",
        market
    )
    img.save("test_post.png")
    print("test_post.png 저장 완료!")