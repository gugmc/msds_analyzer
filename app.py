import streamlit as st
import pdfplumber
import tempfile
import os
import json
import pandas as pd
import time
import re
from datetime import datetime # 🌟 시간 기록을 위한 모듈 추가
from pdf2image import convert_from_path
from ollama import Client 
import requests # 🌟 디스코드로 메시지를 보내기 위한 필수 라이브러리 추가

from cas_db import LEGAL_CAS_DB 

st.set_page_config(page_title="MSDS AI 하이브리드 솔루션", layout="wide")

# ==========================================
# 0. 저장소 폴더 생성 로직
# ==========================================
STORAGE_DIR = "storage"
PDF_STORAGE = os.path.join(STORAGE_DIR, "pdfs")
HISTORY_STORAGE = os.path.join(STORAGE_DIR, "history")

os.makedirs(PDF_STORAGE, exist_ok=True)
os.makedirs(HISTORY_STORAGE, exist_ok=True)

# ==========================================
# 1. 초기화 및 세션 상태 관리
# ==========================================
if "all_results" not in st.session_state: st.session_state.all_results = None
if "messages" not in st.session_state: st.session_state.messages = []

# ==========================================
# 2. 백엔드 및 저장 로직
# ==========================================
def save_file_locally(uploaded_file):
    """업로드된 PDF를 로컬 저장소에 저장합니다."""
    file_path = os.path.join(PDF_STORAGE, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# 🌟 디스코드 실시간 알림 전송 함수 추가
def send_to_discord(results_list):
    # 👇 여기에 디스코드에서 발급받은 '웹훅 URL'을 복사해서 붙여넣으세요!
    WEBHOOK_URL = "https://discordapp.com/api/webhooks/1510658141178691765/0dmyjFWGMmPq-mI5bkYY5ffKQ_AYCGdSpPcPly0qYWnQw_RP1s2Gs6vmjyidf1ZO4_aU" 
    
    if not WEBHOOK_URL or "여기에_복사한_웹훅_주소를_넣으세요" in WEBHOOK_URL:
        return False

    try:
        for item in results_list:
            # 디스코드 채팅창에 예쁘게 보이도록 마크다운 포맷팅
            msg = f"🔔 **새로운 MSDS 분석 완료!**\n" \
                  f"**📄 문서명:** {item['제품명']}\n" \
                  f"**🧪 물질명:** {item['물질명']} (CAS: {item['CAS번호']})\n" \
                  f"**⚖️ 함유량:** {item['최소(%)']} ~ {item['최대(%)']}%\n" \
                  f"**🔍 판정결과:** 작업환경측정({item['작업측정']}) / 특수건강진단({item['특수진단']})\n" \
                  f"**📝 사유:** {item['사유']}\n" \
                  f"**⏱️ 분석일시:** {item['분석일시']}\n" \
                  f"----------------------------------------"
            
            # 디스코드로 전송
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
        
        e_c = response.get('eval_count', 0)
        e_d = response.get('eval_duration', 0)
        p_c = response.get('prompt_eval_count', 0)
        tok_s = e_c / (e_d / 1e9) if e_d > 0 else 0.0
        metrics = {'tokens': p_c + e_c, 'tok_s': round(tok_s, 1)}
        
        match = re.search(r'\[.*\]', raw_output, re.DOTALL)
        if match: return json.loads(match.group(0)), metrics
        return [], metrics
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

# 사이드바: Ngrok API 주소 입력창
st.sidebar.markdown("### 🔌 AI 서버 연결 설정")
api_url = st.sidebar.text_input("Ollama API 주소 (Ngrok URL)", value="http://localhost:11434")
st.sidebar.caption("※ 배포 환경에서는 Ngrok 주소를 입력하세요.")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader("📂 MSDS PDF 업로드", type=["pdf"], accept_multiple_files=True)

tab1, tab2, tab3 = st.tabs(["📊 대상물질 자동 판별", "💬 MSDS 대화형 챗봇 (RAG)", "📁 전체 누적 데이터 보기"])

# ------------------------------------------
# [Tab 1] 자동 판별기 (저장 기능 추가)
# ------------------------------------------
with tab1:
    if uploaded_files:
        preview_data = []
        for file in uploaded_files:
            p_type = check_pdf_type_stream(file)
            preview_data.append({"파일명": file.name, "문서 형태": "텍스트형" if p_type == "TEXT_BASED" else "스캔본", "배정 모델": "gemma4:e2b" if p_type == "TEXT_BASED" else "gemma4:31b"})
        st.table(pd.DataFrame(preview_data))
        
        if st.button("🚀 선택된 파일 분석 시작", type="primary"):
            temp_results = []
            total_files = len(uploaded_files)
            status_text, progress_bar = st.empty(), st.progress(0)
            start_time = time.time()
            
            for idx, uploaded_file in enumerate(uploaded_files):
                f_start = time.time()
                status_text.info(f"🔄 {uploaded_file.name} 처리 중...")
                
                # 🌟 원본 파일을 로컬 저장소에 저장
                saved_pdf_path = save_file_locally(uploaded_file)
                
                # 분석을 위한 임시 경로 사용
                tmp_path = saved_pdf_path 

                p_type = check_pdf_type_stream(uploaded_file)
                iso_text, raw_tables = get_pdf_content(tmp_path)
                ext_json, metrics, track = [], {}, ""
                
                if p_type == "TEXT_BASED":
                    target = "gemma4:e2b"
                    if raw_tables:
                        track = f"Track A ({target})"
                        prompt = "### MSDS DATA\n" + "\n".join(["| " + " | ".join(r) + " |" for r in raw_tables])
                        ext_json, metrics = extract_info_with_ai(prompt, target, api_url=api_url)
                    if not ext_json and len(iso_text) > 50:
                        track = f"Track A-2 ({target})"
                        ext_json, metrics = extract_info_with_ai(f"### TEXT\n{iso_text}", target, api_url=api_url)
                
                if not ext_json:
                    target = "gemma4:31b"
                    track = f"Track B ({target})"
                    images = convert_from_path(tmp_path, first_page=1, last_page=3, dpi=200)
                    img_paths = []
                    for i, img in enumerate(images):
                        p = tmp_path.replace(".pdf", f"_{i}.jpg")
                        img.save(p, 'JPEG'); img_paths.append(p)
                    ext_json, metrics = extract_info_with_ai(None, target, api_url=api_url, is_image=True, image_paths=img_paths)
                    for p in img_paths: os.remove(p)

                if ext_json:
                    for item in ext_json:
                        cas, name, pct = str(item.get("cas", "")).strip(), str(item.get("name", "")), str(item.get("pct", "0"))
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
                            "제품명": uploaded_file.name.replace(".pdf", ""), 
                            "물질명": name, "CAS번호": cas,
                            "최소(%)": format_val(mi), "최대(%)": format_val(ma),
                            "작업측정": we_mark, "특수진단": sh_mark, "모델": track, "사유": reason
                        })
                        
                    f_time = time.time() - f_start
                    st.caption(f"✅ {uploaded_file.name} 분석 완료")
                else:
                    st.error(f"❌ '{uploaded_file.name}' 추출 실패.")
                
                progress_bar.progress((idx + 1) / total_files)
            
            # 🌟 결과 세션 스테이트 저장
            st.session_state.all_results = temp_results

            # 🌟 1. 디스코드 실시간 알림 전송 로직
            if temp_results:
                with st.spinner('Processing...'):
                    send_to_discord(temp_results)
            
            # 🌟 2. 히스토리 폴더에 CSV 파일 자동 저장
            if temp_results:
                history_df = pd.DataFrame(temp_results)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                history_filename = f"result_{timestamp}.csv"
                history_df.to_csv(os.path.join(HISTORY_STORAGE, history_filename), index=False, encoding='utf-8-sig')
                st.success(f"🎉 모든 분석 완료 및 로직 저장됨 (파일명: {history_filename})")

        if st.session_state.all_results:
            st.subheader("📊 통합 판별 결과")
            df = pd.DataFrame(st.session_state.all_results)
            # 결과표에서는 '분석일시'를 빼고 깔끔하게 보여줌
            display_df = df.drop(columns=["분석일시"]) if "분석일시" in df.columns else df
            st.dataframe(display_df.style.map(color_ox, subset=['작업측정', '특수진단']), use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 결과 CSV 다운로드", csv, "MSDS_분석결과.csv", "text/csv")
    else:
        st.info("👈 파일을 업로드해 주세요.")

# ------------------------------------------
# [Tab 2] RAG 챗봇
# ------------------------------------------
with tab2:
    if uploaded_files:
        sel_file = st.selectbox("질문할 문서 선택", [f.name for f in uploaded_files])
        target = next(f for f in uploaded_files if f.name == sel_file)
        
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])
                
        if query := st.chat_input(f"'{sel_file}'에 대해 물어보세요."):
            st.session_state.messages.append({"role": "user", "content": query})
            with st.chat_message("user"): st.markdown(query)
                
            with st.chat_message("assistant"):
                with st.spinner("생각 중..."):
                    txt = extract_full_text_for_rag(target)
                    if "텍스트 추출 불가" in txt:
                        ans = "스캔본 문서는 챗봇 이용이 어렵습니다."
                    else:
                        prompt = f"MSDS 전문가로서 다음 원문을 바탕으로 답하세요.\n[원문]\n{txt[:8000]}\n[질문]\n{query}"
                        try:
                            client = Client(host=api_url)
                            res = client.chat(model='gemma4:e2b', messages=[{'role': 'user', 'content': prompt}])
                            ans = res['message']['content']
                        except Exception as e: ans = f"🚨 API 연결 오류: {e}"
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
    else:
        st.info("👈 파일을 업로드해 주세요.")


# ------------------------------------------
# [Tab 3] 전체 누적 데이터 대시보드 (🔒 관리자 전용 잠금 추가)
# ------------------------------------------
with tab3:
    st.markdown("### 🔒 관리자 데이터 인증")
    
    # 🌟 여기에 연구자님이 사용할 비밀번호를 적어두세요! (기본값: admin1234)
    ADMIN_PASSWORD = "admin1234" 
    
    # 비밀번호 입력창 (type="password"로 설정하면 글자가 ●●●로 가려집니다)
    input_password = st.text_input("보안 비밀번호를 입력하세요", type="password", key="admin_tab_pwd")
    
    if input_password == ADMIN_PASSWORD:
        st.success("🔓 인증에 성공했습니다. 관리자페이지를 표시합니다.")
        st.markdown("---")
        st.markdown("### 📚 서버에 누적된 전체 분석 기록")
        
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
                    st.download_button("📥 통합 데이터 엑셀 다운로드", csv, "MSDS_전체누적데이터.csv", "text/csv")
            else:
                st.info("아직 저장된 분석 기록이 없습니다.")
        else:
            st.info("저장소 폴더가 존재하지 않습니다.")
            
    elif input_password:
        # 비밀번호를 틀렸을 때만 에러 메시지 출력
        st.error("❌ 비밀번호가 일치하지 않습니다. 접근 권한이 없습니다.")
    else:
        # 아무것도 입력하지 않았을 때 나오는 기본 안내문
        st.info("🔑 이 공간은 외부 사용자에게 노출되지 않는 보안 구역입니다. 누적 기록을 보시려면 비밀번호를 입력해 주세요.")



# 🌟 [신규 기능] 사이드바에 서버 저장소 관리 기능 구현 (🔒 탭3 비밀번호와 연동)
st.sidebar.markdown("### 💾 관리자 페이지")
# 사용자가 탭3에서 입력한 비밀번호가 맞았을 때만 사이드바 다운로드 창을 보여줍니다.
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
