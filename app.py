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
    p.drawRightString(width - 50, height - 125, f"문서번호: GIL-MSDS-{get_seoul_time('%m%d%H%M')}-{count:02d}")

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

    min_v = item.get('최소(%)', '0')
    max_v = item.get('최대(%)', '0')
    pct_display = f"{min_v}%" if min_v == max_v else f"{min_v}% ~ {max_v}%"

    rows = [
        ("제 품 명", item.get("제품명", "-")),
        ("물 질 명", item.get("물질명", "-")),
        ("CAS 번호", item.get("CAS번호", "-")),
        ("함 유 량", pct_display),
        ("작업환경 대상", "대상물질 (O)" if item.get("작업환경") == "O" else "미대상 (X)"),
        ("특수검진 대상", "대상물질 (O)" if item.get("특수검진") == "O" else "미대상 (X)"),
        ("배정 AI 모델", item.get("모델", "-")),
    ]

    for label, val in rows:
        draw_row(label, val, y_pos)
        y_pos -= 35

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

    y_pos -= 100
    p.setFont(font_name, 12)
    p.setFillColor(colors.HexColor("#2C3E50"))
    p.drawCentredString(width / 2, y_pos, "본 확인서는 산업안전보건법 및 화학물질관리법 등 관련 규정에 의거하여")
    p.drawCentredString(width / 2, y_pos - 20, "AI 하이브리드 전문가 검증 시스템을 통해 판별 및 검토되었음을 확인합니다.")

    y_pos -= 100
    p.setFont(font_name, 14)
    p.setFillColor(colors.HexColor("#2C3E50"))
    p.drawString(50, y_pos + 20, "가천대길병원 작업환경측정실")

    box_w = 140
    box_h = 60
    start_x = width - 50 - box_w
    start_y = y_pos

    p.setStrokeColor(colors.HexColor("#2C3E50"))
    p.setLineWidth(1)
    p.rect(start_x, start_y, box_w, box_h)
    p.line(start_x + box_w/2, start_y, start_x + box_w/2, start_y + box_h)
    p.line(start_x, start_y + box_h - 20, start_x + box_w, start_y + box_h - 20)

    p.setFont(font_name, 10)
    p.drawCentredString(start_x + box_w/4, start_y + box_h - 14, "담 당")
    p.drawCentredString(start_x + box_w*3/4, start_y + box_h - 14, "책 임")
    p.setFillColor(colors.HexColor("#7F8C8D"))
    p.drawCentredString(start_x + box_w/4, start_y + 15, "(서 명)")
    p.drawCentredString(start_x + box_w*3/4, start_y + 15, "(서 명)")

    p.save()
    buffer.seek(0)
    return buffer

def save_file_locally(file_name, file_bytes):
    file_path = os.path.join(PDF_STORAGE, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return file_path

def send_to_discord(results_list, webhook_url):
    if not webhook_url or "api/webhooks" not in webhook_url:
        return False

    try:
        for item in results_list:
            mi = item.get('최소(%)', '0')
            ma = item.get('최대(%)', '0')
            pct_display = f"{mi}%" if mi == ma else f"{mi}% ~ {ma}%"

            msg = f"""🔔 **새로운 MSDS 분석 완료!**
**📄 문서명:** {item['제품명']}
**🧪 물질명:** {item['물질명']} (CAS: {item['CAS번호']})
**⚖️ 함유량:** {pct_display}
**🔍 판정결과:** 작업환경({item['작업환경']}) / 특수검진({item['특수검진']})
**📝 사유:** {item['사유']}
**⏱️ 분석일시:** {item['분석일시']}
----------------------------------------"""
            res = requests.post(webhook_url, json={"content": msg})
            if res.status_code >= 400:
                st.error(f"🚨 디스코드 서버 거부 (오류코드: {res.status_code})")
        return True
    except Exception as e:
        st.error(f"🚨 디스코드 통신 실패 원인: {e}")
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
    
    sec3_p = re.compile(r"(?:제\s*3\s*항|3\s*\.)\s*(?:구\s*성\s*성\s*분|화\s*학\s*물\s*질|조\s*성|명\s*칭|Composition)", re.IGNORECASE)
    sec4_p = re.compile(r"(?:제\s*4\s*항|4\s*\.)\s*(?:응\s*급\s*조\s*치|First\s*aid)", re.IGNORECASE)
    s_m, e_m = sec3_p.search(full_text.replace(" ", "")), sec4_p.search(full_text.replace(" ", ""))
    
    isolated = ""
    if s_m and e_m and s_m.start() < e_m.start(): 
        isolated = full_text[s_m.start():e_m.start()]
    elif s_m: 
        isolated = full_text[s_m.start():s_m.start()+2000]
    return isolated, extracted_tables

def extract_info_with_ai(prompt_content, target_model, api_url, is_image=False, image_paths=None):
    system_prompt = """당신은 데이터 추출 전문가입니다. MSDS Section 3에서 성분명, CAS번호, 함유량(%)을 추출하세요.
    - CAS번호에 슬래시(/)나 다른 코드(예: KE번호)가 함께 적혀있다면 반드시 숫자-숫자-숫자 형태의 순수 CAS번호 위주로 추출해야 합니다.
    - 반드시 [{"name": "물질명", "cas": "CAS", "pct": "함유량"}] 형식의 JSON 배열로만 답하세요. 부연설명 금지."""
    
    messages = [{'role': 'system', 'content': system_prompt}]
    if is_image and image_paths:
        messages.append({'role': 'user', 'content': "이미지에서 표 데이터를 추출해.", 'images': image_paths})
    else:
        messages.append({'role': 'user', 'content': prompt_content})
        
    try:
        client = Client(host=api_url, headers={"ngrok-skip-browser-warning": "true"})
        response = client.chat(model=target_model, messages=messages)
        raw_output = response['message']['content']
        
        match = re.search(r'\[.*\]', raw_output, re.DOTALL)
        if match: return json.loads(match.group(0)), {}
        return [], {}
    except Exception as e: 
        st.error(f"🚨 AI 서버 연결 오류: {e}")
        return [], {}

def get_min_max_content(content_str):
    if not isinstance(content_str, str): content_str = str(content_str)
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", content_str)
    if nums:
        floats = [float(n) for n in nums]
        return min(floats), max(floats)
    return 0.0, 0.0

def format_val(val):
    try:
        f_val = float(val)
        return f"{int(f_val)}" if f_val.is_integer() else f"{f_val:.1f}"
    except: return "0"

def color_ox(val):
    if str(val).upper() == 'O': return 'color: #e74c3c; font-weight: bold;'
    elif str(val).upper() == 'X': return 'color: #2ecc71; font-weight: bold;'
    return ''

def extract_full_text_for_rag(file_obj):
    full_text = ""
    try:
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: full_text += t + "\n"
    except: full_text = "텍스트 추출 불가 스캔본"
    file_obj.seek(0)
    return full_text

# ==========================================
# 3. Streamlit UI 영역
# ==========================================
st.title("🛡️ AI 산업안전보건 전문가 시스템")

st.sidebar.markdown("### 🔌 AI 서버 연결 설정")
api_url = st.sidebar.text_input("Ollama API 주소 (Ngrok URL)", value="http://localhost:11434")
st.sidebar.caption("※ 배포 환경에서는 Ngrok 주소를 입력하세요.")
st.sidebar.markdown("---")

discord_webhook = ""
if "admin_tab_pwd" in st.session_state and st.session_state["admin_tab_pwd"] == ADMIN_PASSWORD:
    st.sidebar.markdown("### 🔔 시스템 관리 (관리자 전용)")
    st.sidebar.caption("※ 일반 사용자는 이 메뉴를 볼 수 없습니다.")
    # 🌟 입력칸의 기본값을 세션 상태에서 가져오되, 없으면 방금 설정한 기본 URL을 보여줌
    discord_webhook = st.sidebar.text_input("디스코드 웹훅 URL 설정", value=st.session_state.get("discord_webhook_url", DEFAULT_DISCORD_WEBHOOK), type="password", key="discord_webhook_url")
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("### 💾 서버 저장소 관리 (원본 PDF)")
    if os.path.exists(PDF_STORAGE):
        pdf_files = sorted(os.listdir(PDF_STORAGE))
        if pdf_files:
            selected_pdf = st.sidebar.selectbox("과거 업로드된 PDF 선택", pdf_files)
            pdf_path = os.path.join(PDF_STORAGE, selected_pdf)
            with open(pdf_path, "rb") as f:
                st.sidebar.download_button(
                    label="📥 선택한 원본 PDF 다운로드",
                    data=f,
                    file_name=selected_pdf,
                    mime="application/pdf"
                )
        else:
            st.sidebar.caption("저장된 PDF 파일이 없습니다.")
    st.sidebar.markdown("---")
else:
    # 관리자가 아닌 경우 기본 고정된 웹훅 주소를 사용함
    discord_webhook = st.session_state.get("discord_webhook_url", DEFAULT_DISCORD_WEBHOOK)

uploaded_files = st.sidebar.file_uploader("📂 MSDS PDF 또는 ZIP 파일 업로드", type=["pdf", "zip"], accept_multiple_files=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 분석 자동 판별", "📄 리포트 출력 (PDF)", "💬 MSDS 챗봇", "📁 관리자 전용"])

# ------------------------------------------
# [Tab 1] 자동 판별기 
# ------------------------------------------
with tab1:
    if uploaded_files:
        analysis_queue = []
        for f in uploaded_files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(f) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".pdf") and not name.startswith("__MACOSX"):
                            decoded_name = decode_zip_filename(name)
                            pdf_bytes = z.read(name)
                            clean_filename = os.path.basename(decoded_name)
                            analysis_queue.append({
                                "name": clean_filename,
                                "bytes": pdf_bytes,
                                "source": f"ZIP: {f.name}"
                            })
            else:
                clean_name = unicodedata.normalize('NFC', f.name)
                analysis_queue.append({
                    "name": clean_name,
                    "bytes": f.getvalue(),
                    "source": "개별 PDF 업로드"
                })

        preview_data = []
        for item in analysis_queue:
            bio = BytesIO(item["bytes"])
            p_type = check_pdf_type_stream(bio)
            preview_data.append({
                "파일명": item["name"],
                "출처": item["source"],
                "문서 형태": "텍스트형" if p_type == "TEXT_BASED" else "스캔본",
                "배정 모델": "gemma4:e2b" if p_type == "TEXT_BASED" else "gemma4:31b"
            })
            
        st.markdown(f"📋 **분석 대기 중인 문서:** 총 `{len(analysis_queue)}` 건")
        st.table(pd.DataFrame(preview_data))
        
        if st.button("🚀 일괄 대량 분석 및 배치 처리 시작", type="primary"):
            temp_results = []
            total_files = len(analysis_queue)
            status_text, progress_bar = st.empty(), st.progress(0)
            
            for idx, item in enumerate(analysis_queue):
                status_text.info(f"🔄 [{idx+1}/{total_files}] '{item['name']}' 배치 분석 진행 중...")
                
                saved_pdf_path = save_file_locally(item["name"], item["bytes"])
                tmp_path = saved_pdf_path 

                bio = BytesIO(item["bytes"])
                p_type = check_pdf_type_stream(bio)
                iso_text, raw_tables = get_pdf_content(tmp_path)
                ext_json, track = [], ""
                
                if p_type == "TEXT_BASED":
                    target = "gemma4:e2b"
                    if raw_tables:
                        track = f"Track A ({target})"
                        prompt = "### MSDS DATA\n" + "\n".join(["| " + " | ".join(r) + " |" for r in raw_tables])
                        ext_json, _ = extract_info_with_ai(prompt, target, api_url=api_url)
                    if not ext_json and len(iso_text) > 50:
                        track = f"Track A-2 ({target})"
                        ext_json, _ = extract_info_with_ai(f"### TEXT\n{iso_text}", target, api_url=api_url)
                
                if not ext_json:
                    target = "gemma4:31b"
                    track = f"Track B ({target})"
                    try:
                        images = convert_from_path(tmp_path, first_page=1, last_page=3, dpi=200)
                        img_paths = []
                        for i, img in enumerate(images):
                            p = tmp_path.replace(".pdf", f"_{i}.jpg")
                            img.save(p, 'JPEG'); img_paths.append(p)
                        ext_json, _ = extract_info_with_ai(None, target, api_url=api_url, is_image=True, image_paths=img_paths)
                        for p in img_paths: os.remove(p)
                    except:
                        pass

                if ext_json:
                    for element in ext_json:
                        cas, name, pct = str(element.get("cas", "")).strip(), str(element.get("name", "")), str(element.get("pct", "0"))
                        mi, ma = get_min_max_content(pct)
                        clean_name = name.replace(" ", "")
                        
                        if len(name) < 2 and cas == "미상": continue
                        
                        cas_match = re.search(r'\d+-\d+-\d+', cas)
                        if cas_match:
                            cas = cas_match.group(0) 
                        
                        we_mark, sh_mark, reason = "X", "X", "DB 미등록"
                        matched_db_info = None
                        match_type = ""
                        
                        if cas in LEGAL_CAS_DB:
                            matched_db_info = LEGAL_CAS_DB[cas]
                            match_type = "DB 대조"
                        elif "자일렌" in clean_name or "크실렌" in clean_name or "Xylene" in name:
                            matched_db_info = {"WE": "O", "SH": "O", "threshold": 1.0}
                            match_type = "키워드 매칭(자일렌)"
                        elif "크레졸" in clean_name or "Cresol" in name:
                            matched_db_info = {"WE": "O", "SH": "O", "threshold": 1.0}
                            match_type = "키워드 매칭(크레졸)"

                        if matched_db_info:
                            threshold = matched_db_info["threshold"]
                            if ma >= threshold:
                                we_mark, sh_mark = matched_db_info["WE"], matched_db_info["SH"]
                                reason = f"{match_type}: 기준({format_val(threshold)}%) 이상"
                            else:
                                reason = f"{match_type}: 기준({format_val(threshold)}%) 미달"
                        
                        temp_results.append({
                            "분석일시": get_seoul_time(), 
                            "제품명": unicodedata.normalize('NFC', item["name"].replace(".pdf", "")), 
                            "물질명": unicodedata.normalize('NFC', name),
                            "CAS번호": cas,
                            "최소(%)": format_val(mi), "최대(%)": format_val(ma),
                            "작업환경": we_mark, "특수검진": sh_mark, "모델": track, "사유": reason
                        })
                else:
                    st.error(f"❌ '{item['name']}' 정밀 성분 추출 실패.")
                
                progress_bar.progress((idx + 1) / total_files)
            
            st.session_state.all_results = temp_results

            if temp_results and discord_webhook:
                with st.spinner('디스코드 통제실로 분석 현황 전송 중...'):
                    send_to_discord(temp_results, discord_webhook)
            
            if temp_results:
                history_df = pd.DataFrame(temp_results)
                timestamp = get_seoul_time("%Y%m%d_%H%M%S") 
                history_filename = f"batch_result_{timestamp}.csv"
                history_df.to_csv(os.path.join(HISTORY_STORAGE, history_filename), index=False, encoding='utf-8-sig')
                st.success(f"🎉 모든 대량 배치 분석 완료! (파일명: {history_filename})")
                time.sleep(0.5)
                st.rerun()

        if st.session_state.all_results:
            st.subheader("📊 통합 분석 결과 (요약표)")
            df = pd.DataFrame(st.session_state.all_results)
            display_df = df.drop(columns=["분석일시"]) if "분석일시" in df.columns else df
            st.dataframe(display_df.style.map(color_ox, subset=['작업환경', '특수검진']), use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 전체 결과 Excel(.CSV)로 저장", csv, "MSDS_분석결과.csv", "text/csv")
            st.info("💡 **PDF 확인서 출력은 위쪽의 [📄 리포트 출력 (PDF)] 탭을 클릭해 주세요!**")
    else:
        st.info("👈 왼쪽 사이드바에서 PDF 또는 ZIP 파일을 업로드해 주세요.")

# ------------------------------------------
# [Tab 2] 리포트 출력 센터
# ------------------------------------------
with tab2:
    st.subheader("📄 안전보건 요약 리포트 (PDF) 출력 센터")
    
    if st.session_state.all_results:
        st.markdown("분석된 유해화학물질의 개별 판정 결과를 **가천대길병원 공식 확인서 포맷**으로 출력합니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📦 일괄 다운로드 (추천)")
            st.caption("분석된 전체 화학물질 확인서를 하나의 ZIP 파일로 묶어서 받습니다.")
            
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, item in enumerate(st.session_state.all_results):
                    pdf_buffer = generate_pdf_report(item, count=idx+1)
                    safe_prod = item.get("제품명", f"미상_{idx}").replace("/", "_").replace("\\", "_")
                    safe_mat = item.get("물질명", "미상").replace("/", "_").replace("\\", "_")
                    filename = f"확인서_{safe_prod}_{safe_mat}.pdf"
                    zip_file.writestr(filename, pdf_buffer.getvalue())
            
            st.download_button(
                label="📥 모든 확인서 한 번에 다운로드 (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"MSDS_전체확인서_{get_seoul_time('%m%d%H%M')}.zip",
                mime="application/zip",
                type="primary"
            )
            
        with col2:
            st.markdown("#### 📄 개별 선택 다운로드")
            st.caption("목록에서 원하는 단일 물질만 선택하여 PDF로 다운로드합니다.")
            item_options = []
            for i, r in enumerate(st.session_state.all_results):
                item_options.append(f"[{i+1}] {r['제품명']} - {r['물질명']} (CAS: {r['CAS번호']})")
            
            selected_option = st.selectbox("출력 대상 선택", item_options)
            if selected_option:
                selected_idx = int(selected_option.split("]")[0].replace("[", "")) - 1
                target_item = st.session_state.all_results[selected_idx]
                
                pdf_data = generate_pdf_report(target_item, count=selected_idx + 1)
                st.download_button(
                    label=f"📥 {target_item['물질명']} 확인서 다운로드",
                    data=pdf_data,
                    file_name=f"MSDS_확인서_{target_item['물질명']}.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("👈 먼저 [📊 분석 자동 판별] 탭에서 파일을 분석해 주세요. 분석이 완료되어야 출력할 수 있습니다.")

# ------------------------------------------
# [Tab 3] RAG 챗봇
# ------------------------------------------
with tab3:
    if uploaded_files:
        document_names = []
        for f in uploaded_files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(f) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".pdf") and not name.startswith("__MACOSX"):
                            decoded_name = decode_zip_filename(name)
                            document_names.append(os.path.basename(decoded_name))
            else:
                document_names.append(unicodedata.normalize('NFC', f.name))
                
        if document_names:
            sel_file = st.selectbox("질문할 문서 선택", document_names)
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])
                    
            if query := st.chat_input(f"'{sel_file}'에 대해 물어보세요."):
                st.session_state.messages.append({"role": "user", "content": query})
                with st.chat_message("user"): st.markdown(query)
                    
                with st.chat_message("assistant"):
                    with st.spinner("전문 검토 의견 작성 중..."):
                        file_path = os.path.join(PDF_STORAGE, sel_file)
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                txt = extract_full_text_for_rag(f)
                        else:
                            txt = "서버 백업 데이터 활용"
                            
                        if "텍스트 추출 불가" in txt:
                            ans = "해당 문서는 스캔본 이미지 기반이므로 RAG 텍스트 답변이 제한됩니다."
                        else:
                            prompt = f"MSDS 전문가로서 다음 원문을 바탕으로 안전보건법적 관점에서 명확하게 답하세요.\n[원문]\n{txt[:8000]}\n[질문]\n{query}"
                            try:
                                client = Client(host=api_url)
                                res = client.chat(model='gemma4:e2b', messages=[{'role': 'user', 'content': prompt}])
                                ans = res['message']['content']
                            except Exception as e: ans = f"🚨 로컬 Ollama AI 서버 연결 실패: {e}"
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
        else:
            st.info("업로드된 유효한 PDF 문서가 없습니다.")
    else:
        st.info("👈 파일을 업로드해 주세요.")

# ------------------------------------------
# [Tab 4] 관리자 전용 대시보드
# ------------------------------------------
with tab4:
    st.markdown("### 🔒 관리자 통합 통제 대시보드")
    
    input_password = st.text_input("보안 자격증명 비밀번호 입력", type="password", key="admin_tab_pwd")
    
    if input_password == ADMIN_PASSWORD:
        st.success("🔓 중앙 관리자 인증에 성공했습니다. (왼쪽 사이드바에 관리자 메뉴가 활성화되었습니다)")
        st.markdown("---")
        st.markdown("### 📚 전사 누적 분석 빅데이터 기록 (서울 시간 기준)https://iguana-garter-ditch.ngrok-free.dev")
        
        if os.path.exists(HISTORY_STORAGE):
            history_files = [f for f in os.listdir(HISTORY_STORAGE) if f.endswith('.csv')]
            
            if history_files:
                all_data = []
                for file_name in history_files:
                    file_path = os.path.join(HISTORY_STORAGE, file_name)
                    df = pd.read_csv(file_path)
                    all_data.append(df)
                
                if all_data:
                    merged_df = pd.concat(all_data, ignore_index=True)
                    if "분석일시" in merged_df.columns:
                        merged_df = merged_df.sort_values(by="분석일시", ascending=False)
                    
                    st.dataframe(merged_df, use_container_width=True, hide_index=True)
                    
                    csv = merged_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 전사 통합 마스터 데이터 Excel 다운로드", csv, "MSDS_전사마스터기록.csv", "text/csv")
            else:
                st.info("아직 저장소에 누적된 분석 이력이 없습니다.")
        else:
            st.info("저장소 구조 레이어가 존재하지 않습니다.")
            
    elif input_password:
        st.error("❌ 자격증명 비밀번호가 불일치합니다.")
    else:
        st.info("🔑 본 영역은 관리자 전용 암호화 영역입니다. 과거 전체 분석 이력을 추적하시려면 비밀번호를 입력해 주십시오.")
