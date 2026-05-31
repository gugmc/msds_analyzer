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
from pdf2image import convert_from_path
from ollama import Client 
import requests 

# 🌟 PDF 요약 리포트 생성을 위한 reportlab 라이브러리 추가
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

from cas_db import LEGAL_CAS_DB 

st.set_page_config(page_title="MSDS AI 하이브리드 솔루션", layout="wide")

# ==========================================
# 0. 저장소 폴더 생성 로직
# ==========================================
STORAGE_DIR = "storage"
PDF_STORAGE = os.path.join(STORAGE_DIR, "pdfs")
HISTORY_STORAGE = os.path.join(STORAGE_DIR, "history")
FONT_STORAGE = os.path.join(STORAGE_DIR, "fonts")

os.makedirs(PDF_STORAGE, exist_ok=True)
os.makedirs(HISTORY_STORAGE, exist_ok=True)
os.makedirs(FONT_STORAGE, exist_ok=True)

# ==========================================
# 1. 초기화 및 세션 상태 관리
# ==========================================
if "all_results" not in st.session_state: st.session_state.all_results = None
if "messages" not in st.session_state: st.session_state.messages = []

# ==========================================
# 2. 백엔드 및 저장 로직
# ==========================================
@st.cache_data
def download_korean_font():
    """PDF 리포트 내 한글 깨짐 방지를 위해 나눔고딕 폰트를 다운로드합니다."""
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = os.path.join(FONT_STORAGE, "NanumGothic.ttf")
    if not os.path.exists(font_path):
        try:
            res = requests.get(font_url)
            with open(font_path, "wb") as f:
                f.write(res.content)
        except Exception as e:
            return None
    return font_path

def generate_pdf_report(item):
    """선택된 유해물질 항목에 대해 깔끔한 A4 1장짜리 검토 결과 확인서 PDF를 생성합니다."""
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
    p.drawString(50, height - 125, f"발행일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawRightString(width - 50, height - 125, "문서번호: SAN-AI-2026-" + datetime.now().strftime('%m%d%H%M'))

    # 4. 상세 내용 배치 (라벨 - 데이터 테이블 형태 구현)
    y_pos = height - 160
    
    def draw_row(label, val, y):
        # 배경 상자
        p.setFillColor(colors.HexColor("#F8F9FA"))
        p.rect(50, y - 10, 120, 30, fill=True, stroke=False)
        p.setFillColor(colors.HexColor("#FFFFFF"))
        p.rect(170, y - 10, width - 220, 30, fill=True, stroke=False)
        
        # 외곽선
        p.setStrokeColor(colors.HexColor("#E2E8F0"))
        p.setLineWidth(1)
        p.rect(50, y - 10, width - 100, 30, fill=False, stroke=True)
        
        # 텍스트
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
        ("작업환경측정 대상", "대상물질 (O)" if item.get("작업측정") == "O" else "미대상 (X)"),
        ("특수건강진단 대상", "대상물질 (O)" if item.get("특수진단") == "O" else "미대상 (X)"),
        ("배정 AI 모델", item.get("모델", "-")),
    ]

    for label, val in rows:
        draw_row(label, val, y_pos)
        y_pos -= 35

    # 사유 란은 내용이 길 수 있으므로 별도 큰 상자로 처리
    y_pos -= 15
    p.setFillColor(colors.HexColor("#F8F9FA"))
    p.rect(50, y_pos - 50, 120, 70, fill=True, stroke=True)
    p.setFillColor(colors.HexColor("#FFFFFF"))
    p.rect(170, y_pos - 50, width - 220, 70, fill=True, stroke=True)
    
    p.setFont(font_name, 11)
    p.setFillColor(colors.HexColor("#34495E"))
    p.drawString(65, y_pos + 10, "법적 규제 사유")
    
    # 텍스트 줄바꿈 방어 로직 (간이 Wrap)
    reason_text = item.get("사유", "-")
    p.setFont(font_name, 10)
    p.setFillColor(colors.HexColor("#C0392B" if "이상" in reason_text else "#27AE60"))
    
    if len(reason_text) > 40:
        p.drawString(185, y_pos + 15, reason_text[:40])
        p.drawString(185, y_pos - 2, reason_text[40:])
    else:
        p.drawString(185, y_pos + 10, reason_text)

    # 5. 하단 법적 공인 문구 및 직인 란
    y_pos -= 120
    p.setFont(font_name, 12)
    p.setFillColor(colors.HexColor("#2C3E50"))
    p.drawCentredString(width / 2, y_pos, "본 확인서는 산업안전보건법 및 화학물질관리법 등 관련 규정에 의거하여")
    p.drawCentredString(width / 2, y_pos - 20, "AI 하이브리드 전문가 검증 시스템을 통해 판별 및 검토되었음을 확인합니다.")

    y_pos -= 80
    p.setFont(font_name, 14)
    p.drawCentredString(width / 2, y_pos, "AI 산업안전보건 검증 시스템 연구 책임자 (인)")
    
    # 가상 직인 도장 그리기
    p.setStrokeColor(colors.HexColor("#E74C3C"))
    p.setLineWidth(1.5)
    p.setFillColor(colors.transparent)
    p.circle(width / 2 + 130, y_pos + 3, 18, stroke=True, fill=False)
    p.setFont(font_name, 8)
    p.setFillColor(colors.HexColor("#E74C3C"))
    p.drawCentredString(width / 2 + 130, y_pos, "안전")
    p.drawCentredString(width / 2 + 130, y_pos - 8, "검증")

    p.save()
    buffer.seek(0)
    return buffer

def save_file_locally(file_name, file_bytes):
    """업로드된 PDF 파일 바이트를 로컬 저장소에 저장합니다."""
    file_path = os.path.join(PDF_STORAGE, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return file_path

def send_to_discord(results_list):
    # 👇 여기에 디스코드에서 발급받은 '웹훅 URL'을 복사해서 붙여넣으세요!
    WEBHOOK_URL = "https://discord.com/api/webhooks/여기에_복사한_웹훅_주소를_넣으세요" 
    
    if not WEBHOOK_URL or "여기에_복사한_웹훅_주소를_넣으세요" in WEBHOOK_URL:
        return False

    try:
        for item in results_list:
            msg = f"🔔 **새로운 MSDS 분석 완료!**\n" \
                  f"**📄 문서명:** {item['제품명']}\n" \
                  f"**🧪 물질명:** {item['물질명']} (CAS: {item['CAS번호']})\n"                   f"**⚖️ 함유량:** {item['최소(%)']} ~ {item['최대(%)']}%\n" \
                  f"**🔍 판정결과:** 작업환경측정({item['작업측정']}) / 특수건강진단({item['특수진단']})\n" \
                  f"**📝 사유:** {item['사유']}\n" \
                  f"**⏱️ 분석일시:** {item['분석일시']}\n"                   f"----------------------------------------"
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
    
    sec3_p = re.compile(r"(?:제\s*3\s*항|3\s*\.)\s*(?:구\s*성\s*성\s*분|화\s*학\s*물\s*질|조\s*성|명\s*칭|Composition)", re.IGNORECASE)
    sec4_p = re.compile(r"(?:제\s*4\s*항|4\s*\.)\s*(?:응\s*급\s*조\s*치|First\s*aid)", re.IGNORECASE)
    s_m, e_m = sec3_p.search(full_text), sec4_p.search(full_text)
    
    isolated = ""
    if s_m and e_m and s_m.start() < e_m.start(): isolated = full_text[s_m.start():e_m.start()]
    elif s_m: isolated = full_text[s_m.start():s_m.start()+2000]
    return isolated, extracted_tables

def extract_info_with_ai(prompt_content, target_model, api_url, is_image=False, image_paths=None):
    system_prompt = """당신은 데이터 추출 전문가입니다. MSDS Section 3에서 성분명, CAS번호, 함유량(%)을 추출하세요.
    - CAS는 [숫자-숫자-숫자] 형태입니다. 없으면 "미상"으로 적으세요.
    - 반드시 [{"name": "물질명", "cas": "CAS", "pct": "함유량"}] 형식의 JSON 배열로만 답하세요. 부연설명 금지."""
    
    messages = [{'role': 'system', 'content': system_prompt}]
    if is_image and image_paths:
        messages.append({'role': 'user', 'content': "이미지에서 표 데이터를 추출해.", 'images': image_paths})
    else:
        messages.append({'role': 'user', 'content': prompt_content})
        
    try:
        client = Client(host=api_url)
        response = client.chat(model=target_model, messages=messages)
        raw_output = response['message']['content']
        
        match = re.search(r'\[.*\]', raw_output, re.DOTALL)
        if match: return json.loads(match.group(0)), {}
        return [], {}
    except Exception as e: 
        st.error(f"🚨 API 연결 오류: {e}")
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
# 3. Streamlit UI
# ==========================================
st.title("🛡️ AI 산업안전보건 전문가 시스템")

# 사이드바 설정
st.sidebar.markdown("### 🔌 AI 서버 연결 설정")
api_url = st.sidebar.text_input("Ollama API 주소 (Ngrok URL)", value="http://localhost:11434")
st.sidebar.caption("※ 배포 환경에서는 Ngrok 주소를 입력하세요.")
st.sidebar.markdown("---")

# 사이드바에 서버 저장소 관리 기능 구현
st.sidebar.markdown("### 💾 서버 저장소 관리")
if "admin_tab_pwd" in st.session_state and st.session_state["admin_tab_pwd"] == "admin1234":
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
else:
    st.sidebar.caption("🔒 관리자 인증 시 활성화됩니다.")
st.sidebar.markdown("---")

# 🌟 짚(ZIP) 파일과 PDF 다중 업로드를 수용하도록 확장
uploaded_files = st.sidebar.file_uploader("📂 MSDS PDF 또는 ZIP 파일 업로드", type=["pdf", "zip"], accept_multiple_files=True)

tab1, tab2, tab3 = st.tabs(["📊 대상물질 자동 판별", "💬 MSDS 대화형 챗봇 (RAG)", "📁 전체 누적 데이터 보기"])

# ------------------------------------------
# [Tab 1] 자동 판별기 (ZIP 해제 및 일괄 대량 처리 구현)
# ------------------------------------------
with tab1:
    if uploaded_files:
        # 업로드 큐 빌드 (ZIP 파일 내부 탐색 포함)
        analysis_queue = []
        
        for f in uploaded_files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(f) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".pdf") and not name.startswith("__MACOSX"):
                            pdf_bytes = z.read(name)
                            clean_filename = os.path.basename(name)
                            analysis_queue.append({
                                "name": clean_filename,
                                "bytes": pdf_bytes,
                                "source": f"ZIP: {f.name}"
                            })
            else:
                analysis_queue.append({
                    "name": f.name,
                    "bytes": f.getvalue(),
                    "source": "개별 PDF 업로드"
                })

        # 미리보기 정보 출력
        preview_data = []
        for item in analysis_queue:
            # 텍스트 스캔본 여부를 바이트 스트림 형태로 간이 체크
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
            start_time = time.time()
            
            for idx, item in enumerate(analysis_queue):
                f_start = time.time()
                status_text.info(f"🔄 [{idx+1}/{total_files}] '{item['name']}' 배치 분석 진행 중...")
                
                # 원본 바이트 파일 디스크에 실시간 백업 저장
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
                            "분석일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "제품명": item["name"].replace(".pdf", ""), 
                            "물질명": name, "CAS번호": cas,
                            "최소(%)": format_val(mi), "최대(%)": format_val(ma),
                            "작업측정": we_mark, "특수진단": sh_mark, "모델": track, "사유": reason
                        })
                else:
                    st.error(f"❌ '{item['name']}' 정밀 성분 추출 실패.")
                
                progress_bar.progress((idx + 1) / total_files)
            
            st.session_state.all_results = temp_results

            # 1. 디스코드 실시간 배치 알림 전송 로직
            if temp_results:
                with st.spinner('디스코드 통제실로 분석 현황 전송 중...'):
                    send_to_discord(temp_results)
            
            # 2. 히스토리 폴더에 CSV 파일 통합 자동 저장
            if temp_results:
                history_df = pd.DataFrame(temp_results)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                history_filename = f"batch_result_{timestamp}.csv"
                history_df.to_csv(os.path.join(HISTORY_STORAGE, history_filename), index=False, encoding='utf-8-sig')
                st.success(f"🎉 모든 대량 배치 분석 완료 및 저장 완료! (파일명: {history_filename})")
                time.sleep(0.5)
                st.rerun()

        if st.session_state.all_results:
            st.subheader("📊 배치 처리 통합 분석 결과")
            df = pd.DataFrame(st.session_state.all_results)
            display_df = df.drop(columns=["분석일시"]) if "분석일시" in df.columns else df
            st.dataframe(display_df.style.map(color_ox, subset=['작업측정', '특수진단']), use_container_width=True, hide_index=True)
            
            # 엑셀 통합본 다운로드
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 통합 분석 결과 Excel(.CSV) 다운로드", csv, "MSDS_통합배치결과.csv", "text/csv")
            
            # 🌟 [신규 기능 4] 한 줄 결과물에서 원하는 개별 유해물질 요약 리포트(A4 PDF) 출력 섹션 구현
            st.markdown("---")
            st.subheader("📄 개별 안전보건 요약 리포트 생성 (PDF)")
            st.caption("확인서 출력을 원하시는 특정 화학물질 성분을 선택하면 1장짜리 깔끔한 정식 PDF 서류 보고서가 발행됩니다.")
            
            # 셀렉트박스 가독성을 위한 포맷 매핑
            item_options = []
            for i, r in enumerate(st.session_state.all_results):
                item_options.append(f"[{i+1}] {r['제품명']} - {r['물질명']} (CAS: {r['CAS번호']})")
            
            selected_option = st.selectbox("리포트 출력 대상 성분 선택", item_options)
            if selected_option:
                selected_idx = int(selected_option.split("]")[0].replace("[", "")) - 1
                target_item = st.session_state.all_results[selected_idx]
                
                pdf_data = generate_pdf_report(target_item)
                st.download_button(
                    label=f"📥 {target_item['물질명']} 요약 리포트(PDF) 다운로드",
                    data=pdf_data,
                    file_name=f"MSDS_검토결과확인서_{target_item['물질명']}.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("👈 왼쪽 사이드바에서 복수의 MSDS PDF 파일 또는 대량의 PDF가 패키징된 .ZIP 파일을 업로드해 주세요.")

# ------------------------------------------
# [Tab 2] RAG 챗봇
# ------------------------------------------
with tab2:
    if uploaded_files:
        # 챗봇용 타겟 문서 정리 (ZIP 및 개별 파일 병합 대응)
        document_names = []
        for f in uploaded_files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(f) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".pdf") and not name.startswith("__MACOSX"):
                            document_names.append(os.path.basename(name))
            else:
                document_names.append(f.name)
                
        if document_names:
            sel_file = st.selectbox("질문할 문서 선택", document_names)
            
            # 실시간 가상 파일 오브젝트 로딩 모방
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])
                    
            if query := st.chat_input(f"'{sel_file}'에 대해 물어보세요."):
                st.session_state.messages.append({"role": "user", "content": query})
                with st.chat_message("user"): st.markdown(query)
                    
                with st.chat_message("assistant"):
                    with st.spinner("전문 검토 의견 작성 중..."):
                        # RAG 파일 가상 텍스트 탐색 (물리 경로 연계)
                        file_path = os.path.join(PDF_STORAGE, sel_file)
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                txt = extract_full_text_for_rag(f)
                        else:
                            txt = "서버 백업 데이터 활용"
                            
                        if "텍스트 추출 불가" in txt:
                            ans = "해당 문서는 스캔본 이미지 기반이므로 RAG 텍스트 챗봇 기반 답변 생성이 제한됩니다. 자동 판별기 탭의 AI 추출 데이터를 참고해 주세요."
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
# [Tab 3] 전체 누적 데이터 대시보드 (🔒 관리자 전용 잠금)
# ------------------------------------------
with tab3:
    st.markdown("### 🔒 관리자 통합 통제 대시보드")
    ADMIN_PASSWORD = "admin1234" 
    
    input_password = st.text_input("보안 자격증명 비밀번호 입력", type="password", key="admin_tab_pwd")
    
    if input_password == ADMIN_PASSWORD:
        st.success("🔓 중앙 관리자 인증에 성공했습니다.")
        st.markdown("---")
        st.markdown("### 📚 전사 누적 분석 빅데이터 기록")
        
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
