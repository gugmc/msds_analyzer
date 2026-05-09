import streamlit as st
import pdfplumber
import tempfile
import os
import json
import pandas as pd
import time
import re
from pdf2image import convert_from_path
# 🌟 로컬이 아닌 외부 API 주소로 접속하기 위해 Client 모듈을 추가로 불러옵니다.
from ollama import Client 

from cas_db import LEGAL_CAS_DB 

st.set_page_config(page_title="MSDS AI 하이브리드 솔루션", layout="wide")

# ==========================================
# 1. 초기화 및 세션 상태 관리
# ==========================================
if "all_results" not in st.session_state: st.session_state.all_results = None
if "messages" not in st.session_state: st.session_state.messages = []

# ==========================================
# 2. 백엔드 로직
# ==========================================
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

# 🌟 외부 API URL을 매개변수로 받도록 수정
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
        # 🌟 로컬 호스트가 아닌 사용자가 입력한 API 서버(Ngrok)로 연결!
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

# 🌟 사이드바: Ngrok API 주소 입력창 추가
st.sidebar.markdown("### 🔌 AI 서버 연결 설정")
api_url = st.sidebar.text_input("Ollama API 주소 (Ngrok URL)", value="http://localhost:11434")
st.sidebar.caption("※ 배포 환경에서는 Ngrok이 생성한 주소를 입력하세요. (예: https://abc.ngrok-free.app)")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader("📂 MSDS PDF 업로드", type=["pdf"], accept_multiple_files=True)

tab1, tab2 = st.tabs(["📊 대상물질 자동 판별", "💬 MSDS 대화형 챗봇 (RAG)"])

# ------------------------------------------
# [Tab 1] 자동 판별기
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
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                p_type = check_pdf_type_stream(uploaded_file)
                iso_text, raw_tables = get_pdf_content(tmp_path)
                ext_json, metrics, track = [], {}, ""
                
                if p_type == "TEXT_BASED":
                    target = "gemma4:e2b"
                    if raw_tables:
                        track = f"Track A ({target})"
                        prompt = "### MSDS DATA\n" + "\n".join(["| " + " | ".join(r) + " |" for r in raw_tables])
                        ext_json, metrics = extract_info_with_ai(prompt, target, api_url=api_url) # 🌟 API URL 전달
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
                        if len(name) < 2 and cas == "미상": continue
                        
                        we, sh, reas = "X", "X", "대상 아님"
                        if cas in LEGAL_CAS_DB:
                            db = LEGAL_CAS_DB[cas]
                            if ma >= db["threshold"]:
                                we, sh, reas = db["WE"], db["SH"], f"법적 기준({format_val(db['threshold'])}%) 이상"
                        
                        temp_results.append({
                            "제품명": uploaded_file.name.replace(".pdf", ""), "물질명": name, "CAS번호": cas,
                            "최소(%)": format_val(mi), "최대(%)": format_val(ma),
                            "작업측정": we, "특수진단": sh, "모델": track, "사유": reas
                        })
                    f_time = time.time() - f_start
                    st.caption(f"✅ {uploaded_file.name} 완료: {f_time:.1f}s | {metrics.get('tokens',0)}t | {metrics.get('tok_s',0.0)}t/s")
                
                os.remove(tmp_path)
                progress_bar.progress((idx + 1) / total_files)
            
            st.session_state.all_results = temp_results
            status_text.success(f"🎉 분석 완료 (총 {time.time()-start_time:.1f}초)")

        if st.session_state.all_results:
            st.subheader("📊 통합 판별 결과")
            df = pd.DataFrame(st.session_state.all_results)
            st.dataframe(df.style.map(color_ox, subset=['작업측정', '특수진단']), use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Excel 다운로드", csv, "MSDS_분석결과.csv", "text/csv")
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
                            # 🌟 챗봇도 외부 API로 연결되게 수정
                            client = Client(host=api_url)
                            res = client.chat(model='gemma4:e2b', messages=[{'role': 'user', 'content': prompt}])
                            ans = res['message']['content']
                        except Exception as e: ans = f"🚨 API 연결 오류: {e}"
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
    else:
        st.info("👈 파일을 업로드해 주세요.")