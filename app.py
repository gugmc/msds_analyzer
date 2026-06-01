import streamlit as st
import pdfplumber
import tempfile
import os
import json
import pandas as pd
import time
import re
import zipfile
from io import BytesIO
from datetime import datetime 
import pytz 
from pdf2image import convert_from_path
from ollama import Client 
import requests 

# PDF 요약 리포트 생성을 위한 reportlab 라이브러리
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

from cas_db import LEGAL_CAS_DB 

st.set_page_config(page_title="MSDS AI 하이브리드 솔루션", layout="wide")

# ==========================================
# 0. 저장소 폴더 생성 및 시간대 로직
# ==========================================
STORAGE_DIR = "storage"
PDF_STORAGE = os.path.join(STORAGE_DIR, "pdfs")
HISTORY_STORAGE = os.path.join(STORAGE_DIR, "history")
FONT_STORAGE = os.path.join(STORAGE_DIR, "fonts")

os.makedirs(PDF_STORAGE, exist_ok=True)
os.makedirs(HISTORY_STORAGE, exist_ok=True)
os.makedirs(FONT_STORAGE, exist_ok=True)

def get_seoul_time(format_str="%Y-%m-%d %H:%M:%S"):
    seoul_tz = pytz.timezone("Asia/Seoul")
    return datetime.now(seoul_tz).strftime(format_str)

# 🌟 [개선] 윈도우 ZIP 한글 파일명 깨짐 완벽 복원 함수
def decode_zip_filename(name):
    try:
        # 윈도우(EUC-KR/CP949) 환경 압축 해제
        return name.encode('cp437').decode('cp949')
    except:
        try:
            # Mac 등 UTF-8 환경 압축 해제
            return name.encode('cp437').decode('utf-8')
        except:
            return name

# ==========================================
# 1. 초기화 및 세션 상태 관리
# ==========================================
if "all_results" not in st.session_state: st.session_state.all_results = None
if "messages" not in st.session_state: st.session_state.messages = []

# ==========================================
# 2. 백엔드 및 저장 로직
# ==========================================
@st.cache_data(show_spinner=False)
def download_korean_font():
    """PDF 리포트 내 한글 깨짐 방지를 위해 가장 안정적인 경로에서 폰트를 다운로드합니다."""
    font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = os.path.join(FONT_STORAGE, "NanumGothic.ttf")
    
    # 폰트 파일이 없거나, 다운로드 중 끊겨서 용량이 0인 경우 재다운로드
    if not os.path.exists(font_path) or os.path.getsize(font_path) < 10000:
        try:
            res = requests.get(font_url)
            res.raise_for_status()
            with open(font_path, "wb") as f:
                f.write(res.content)
        except Exception as e:
            return None
    return font_path

def generate_pdf_report(item, count=1):
    """선택된 유해물질 항목에 대해 깔끔한 A4 1장짜리 검토 결과 확인서 PDF를 생성합니다."""
    font_path = download_korean_font()
    font_name = "Helvetica" # 한글 실패 시 기본 폰트
    
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('NanumGothic', font_path))
            font_name = 'NanumGothic'
        except:
            pass

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 1. 문서 테두리 및 가이드라인
    p.setStrokeColor(colors.HexColor("#2C3E50"))
    p.setLineWidth(2)
    p.rect(30, 30, width - 60, height - 60)
    
    p.setStrokeColor(colors.HexColor("#BDC3C7"))
    p.setLineWidth(0.5)
    p.rect(35, 35, width - 70, height - 70)

    # 2. 타이틀 영역
    p.setFont(font_name, 24)
    p.setFillColor(colors.HexColor("#2C3E50"))
    p.drawCentredString(width / 2, height - 80, "MSDS 검토 결과 확인서")
    
    p.setStrokeColor(colors.HexColor("#2C3E50"))
    p.setLineWidth(1.5)
    p.line(50, height - 100, width - 50, height - 100)

    # 3. 문서 정보 표 헤더 스타일 메타데이터 정보
    p.setFont(font_name, 10)
    p.setFillColor(colors.HexColor("#7F8C8D"))
    p.drawString(50, height - 125, f"발행일시: {get_seoul_time()}")
    p.drawRightString(width - 50, height - 125, f"문서번호: GIL-MSDS-{get_seoul_time('%m%d%H%M')}-{count:02d}")

    # 4. 상세 내용 배치
    y_pos = height - 160
    
    def draw_row(label, val, y):
        p.setFillColor(colors.HexColor("#F8F9FA"))
        p.rect(50, y - 10, 120, 30, fill=True, stroke=False)
        p.setFillColor(colors.HexColor("#FFFFFF"))
        p.rect(170, y - 10, width - 220, 30, fill=True, stroke=False)
        
        p.setStrokeColor(colors.HexColor("#E2E8F0"))
        p.setLineWidth(1)
        p.rect(50, y - 10, width - 100, 30, fill=False, stroke=True)
        
        p.setFont(font_name, 11)
        p.setFillColor(colors.HexColor("#34495E"))
        p.drawString(65, y + 2, label)
        
        p.setFont(font_name, 11)
        p.setFillColor(colors.HexColor("#2C3E50"))
        p.drawString(185, y + 2, str(val))

    rows = [
        ("제 품 명", item.get("제품명", "-")),
        ("물 질 명", item.get("물질명", "-")),
        ("CAS 번호", item.get("CAS번호", "-")),
        ("함 유 량", f"{item.get('최소(%)', '0')}% ~ {item.get('최대(%)', '0')}%"),
        ("작업환경 대상", "대상물질 (O)" if item.get("작업환경") == "O" else "미대상 (X)"),
        ("특수검진 대상", "대상물질 (O)" if item.get("특수검진") == "O" else "미대상 (X)"),
        ("배정 AI 모델", item.get("모델", "-")),
    ]

    for label, val in rows:
        draw_row(label, val, y_pos)
        y_pos -= 35

    # 법적 규제 사유 상자
    y_pos -= 15
    box_height = 70
    p.setFillColor(colors.HexColor("#F8F9FA"))
    p.rect(50, y_pos - 50, 120, box_height, fill=True, stroke=True)
    p.setFillColor(colors.HexColor("#FFFFFF"))
    p.rect(170, y_pos - 50, width - 220, box_height, fill=True, stroke=True)
    
    p.setFont(font_name, 11)
    p.setFillColor(colors.HexColor("#34495E"))
    p.drawString(65, y_pos - 19, "법적 규제 사유")
    
    reason_text = item.get("사유", "-")
    p.setFont(font_name, 10)
    p.setFillColor(colors.HexColor("#C0392B" if "이상" in reason_text else "#27AE60"))
    
    if len(reason_text) > 40:
        p.drawString(185, y_pos - 10, reason_text[:40])
        p.drawString(185, y_pos - 28, reason_text[40:])
    else:
        p.drawString(185, y_pos - 19, reason_text)

    # 5. 하단 서명란 (🌟 '기인' 단어 삭제)
    y_pos -= 120
    p.setFont(font_name, 12)
    p.setFillColor(colors.HexColor("#2C3E50"))
    p.drawCentredString(width / 2, y_pos, "본 확인서는 산업안전보건법 및 화학물질관리법 등 관련 규정에 의거하여")
    p.drawCentredString(width / 2, y_pos - 20, "AI 하이브리드 전문가 검증 시스템을 통해 판별 및 검토되었음을 확인합니다.")

    y_pos -= 65
    p.setFont(font_name, 11)
    p.setFillColor(colors.HexColor("#34495E"))
    p.drawString(70, y_pos, "담 당 자 성 명 :  ____________________")
    p.drawString(70, y_pos - 25, "서 명 :  ____________________")

    y_pos -= 65
    p.setFont(font_name, 14)
    p.setFillColor(colors.HexColor("#2C3E50"))
    p.drawCentredString(width / 2, y_pos, "가천대길병원 작업환경측정실 책임자")

    p.save()
    buffer.seek(0)
    return buffer

def save_file_locally(file_name, file_bytes):
    file_path = os.path.join(PDF_STORAGE, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return file_path

def send_to_discord(results_list):
    WEBHOOK_URL = "https://discord.com/api/webhooks/여기에_복사한_웹훅_주소를_넣으세요" 
    
    if not WEBHOOK_URL or "여기에_복사한_웹훅_주소를_넣으세요" in WEBHOOK_URL:
        return False

    try:
        for item in results_list:
            msg = f"🔔 **새로운 MSDS 분석 완료!**\n" \
                  f"**📄 문서명:** {item['제품명']}\n" \
                  f"**🧪 물질명:** {item['물질명']} (CAS: {item['CAS번호']})\n" \
                  f"**⚖️ 함유량:** {item['최소(%)']} ~ {item['최대(%)']}%\n" \
                  f"**🔍 판정결과:** 작업환경({item['작업환경']}) / 특수검진({item['특수검진']})\n" \
                  f"**📝 사유:** {item['사유']}\n" \
                  f"**⏱️ 분석일시(서울):** {item['분석일시']}\n" \
                  f"----------------------------------------"
            requests.post(WEBHOOK_URL, json={"content": msg})
        return True
    except Exception as e:
        st.error(f"🚨 디스코드 알림 전송 실패: {e}")
        return False

def check_pdf_type_stream(file_obj):
    text_content = ""
    try:
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text: text_content += text
    except Exception: pass
    file_obj.seek(0) 
    return "TEXT_BASED" if len(text_content.strip()) > 50 else "IMAGE_BASED"

def get_pdf_content(file_path):
    full_text, extracted_tables = "", []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages[:4]:
            t = page.extract_text()
            if t: full_text += t + "\n"
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or all(cell is None or str(cell).strip() == '' for cell in row): continue
                    extracted_tables.append([str(cell).replace('\n', ' ').strip() if cell else "" for cell in row])
    
    sec3_p = re.compile(r"(?:제\s*3\s*항|3\s*\.)\s*(?:구\s*성\s*성\s*분
