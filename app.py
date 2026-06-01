import streamlit as st
import pdfplumber
import tempfile
import os
import json
import pandas as pd
import time
import re
import zipfile
import unicodedata 
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
# 0. 전역 설정 및 저장소 폴더 생성 
# ==========================================
ADMIN_PASSWORD = "admin1234" 

# 🌟 [개선] 디스코드 웹훅 기본값 고정
DEFAULT_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1510658141178691765/0dmyjFWGMmPq-mI5bkYY5ffKQ_AYCGdSpPcPly0qYWnQw_RP1s2Gs6vmjyidf1ZO4_aU"

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

def decode_zip_filename(name):
    try:
        decoded = name.encode('cp437').decode('cp949')
    except:
        try:
            decoded = name.encode('cp437').decode('utf-8')
        except:
            decoded = name
    return unicodedata.normalize('NFC', decoded)

# ==========================================
# 1. 초기화 및 세션 상태 관리
# ==========================================
if "all_results" not in st.session_state: st.session_state.all_results = None
if "messages" not in st.session_state: st.session_state.messages = []
# 🌟 세션 시작 시 기본 웹훅 주소로 자동 세팅
if "discord_webhook_url" not in st.session_state: st.session_state.discord_webhook_url = DEFAULT_DISCORD_WEBHOOK

# ==========================================
# 2. 백엔드 및 저장 로직
# ==========================================
@st.cache_data(show_spinner=False)
def download_korean_font():
    font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = os.path.join(FONT_STORAGE, "NanumGothic.ttf")
    
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
    font_path = download_korean_font()
    font_name = "Helvetica" 
    
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('NanumGothic', font_path))
            font_name = 'NanumGothic'
        except:
            pass

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setStrokeColor(colors.HexColor("#2C3E50"))
    p.setLineWidth(2)
    p.rect(30, 30, width - 60, height - 60)
    p.setStrokeColor(colors.HexColor("#BDC3C7"))
    p.setLineWidth(0.5)
    p.rect(35, 35, width - 70, height - 70)

    p.setFont(font_name, 24)
    p.setFillColor(colors.HexColor("#2C3E50"))
    p.drawCentredString(width / 2, height - 80, "MSDS 검토 결과 확인서")
    
    p.setStrokeColor(colors.HexColor("#2C3E50"))
    p.setLineWidth(1.5)
    p.line(50, height - 100, width - 50, height - 100)

    p.setFont(font_name, 10)
    p.setFillColor(colors.HexColor("#7F8C8D"))
    p.drawString(50, height - 125, f"발행일시: {get_seoul_time()}")
    p.drawRightString(width - 50, height - 125, f"문서번호: GIL-MSDS-{get_seoul_time('%m%d%
