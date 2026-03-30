import os
import time
import requests
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- 환경 변수 로드 ---
TARGET_DATE = os.environ.get('TARGET_DATE')
MOVIE_TITLE = os.environ.get('MOVIE_TITLE', '')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message})

def get_latest_command():
    """텔레그램 최신 명령어 추출"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res["ok"] and res["result"]:
            valid_commands = []
            for update in res["result"]:
                msg = update.get("message", {})
                text = msg.get("text", "")
                user_id = str(msg.get("from", {}).get("id", ""))
                if user_id == CHAT_ID and text.startswith("/set"):
                    valid_commands.append(text)
            
            if valid_commands:
                last_command = valid_commands[-1]
                parts = last_command.split(" ")
                new_date = re.sub(r'[^0-9]', '', parts[1]) if len(parts) >= 2 else TARGET_DATE
                new_title = " ".join(parts[2:]) if len(parts) > 2 else ""
                return new_date, new_title
    except: pass
    return TARGET_DATE, MOVIE_TITLE

def check_cgv_online():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        current_date, current_title = get_latest_command()
        
        # 텔레그램 명령이 바뀌었음을 인지시키기 위한 로그
        print(f"🔎 검사 시작: 날짜({current_date}), 영화({current_title})")
        
        url = f"https://m.cgv.co.kr/Schedule/?theaterCode=0281&playDate={current_date}"
        driver.get(url)
        time.sleep(15) # 충분한 로딩 대기

        page_source = driver.page_source
        
        # [검증 1] 현재 페이지가 내가 요청한 '그 날짜'가 맞는지 엄격하게 확인
        # CGV 모바일은 선택된 날짜를 "2026.04.07" 형식으로 특정 영역에 표시함
        formatted_date = f"{current_date[:4]}.{current_date[4:6]}.{current_date[6:]}"
        
        # 만약 요청한 날짜 텍스트가 페이지 소스 상의 '날짜 선택 영역'에 포함되어 있지 않다면 리다이렉트된 것임
        # 더 정확하게 하기 위해 "YYYY.MM.DD" 패턴이 페이지에 있는지 확인
        if formatted_date not in page_source:
            print(f"⚠️ 경고: {current_date} 페이지가 아닙니다. (CGV 자동 날짜 이동 감지)")
            return

        # [검증 2] 날짜는 맞는데, 실제로 상영 시간표 데이터가 로드되었는지 확인
        # 시간표가 없으면 '상영 가능한 시간이 없습니다' 등의 메시지가 뜸
        if "hall_name" not in page_source and "상영시간표" not in page_source:
            print(f"⏳ {current_date}: 날짜 페이지는 열렸으나 상영 정보가 아직 없습니다.")
            return

        # [검증 3] IMAX 관이 있고, 영화 제목이 일치하는지 확인
        source_upper = page_source.upper()
        if "IMAX" in source_upper:
            if not current_title or current_title.upper() in source_upper:
                # 최종 확인 성공 시에만 텔레그램 발송
                send_telegram(f"🎯 [진짜오픈!] {current_date} {current_title} IMAX 감지!\n지금 바로 예매하세요!")
                print(f"🔔 알림 발송 완료: {current_date}")
            else:
                print(f"❄️ IMAX는 있으나 영화 제목({current_title})이 일치하지 않음.")
        else:
            print(f"❄️ {current_date}: 일반관만 오픈됨 (IMAX 없음).")

    except Exception as e:
        print(f"❌ 에러: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_cgv_online()
