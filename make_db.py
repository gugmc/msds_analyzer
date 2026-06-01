import pandas as pd
import re
import json

# 엑셀 파일 이름이 다르면 이 부분을 수정해주세요
file_path = "화학물질 및 물리적 인자의 노출기준.csv" 

print("데이터를 스캔하는 중입니다...")
try:
    df = pd.read_csv(file_path, encoding='utf-8', header=None)
except UnicodeDecodeError:
    df = pd.read_csv(file_path, encoding='cp949', header=None)

full_db = {}
for idx, row in df.iterrows():
    if idx < 7: continue # 헤더 건너뛰기
    
    def clean_cell(val):
        return str(val).strip() if pd.notna(val) and str(val).strip() != 'nan' else "-"
    
    ko_name = clean_cell(row[1])
    if ko_name == "-": continue
        
    en_name = clean_cell(row[2])
    formula = clean_cell(row[3])
    twa_ppm = clean_cell(row[4])
    twa_mg = clean_cell(row[5])
    stel_ppm = clean_cell(row[6])
    stel_mg = clean_cell(row[7])
    remark = clean_cell(row[8])
    
    cas_match = re.search(r'\[?(\d{2,7}-\d{2}-\d)\]?', remark)
    cas_key = cas_match.group(1) if cas_match else ko_name 
    
    full_db[cas_key] = {
        "국문표기": ko_name,
        "영문표기": en_name,
        "화학식": formula,
        "TWA(ppm)": twa_ppm,
        "TWA(mg/m3)": twa_mg,
        "STEL(ppm)": stel_ppm,
        "STEL(mg/m3)": stel_mg,
        "비고": remark
    }

# 파이썬 파일(.py) 형태로 저장하기
out = "# exposure_db.py\n\n"
out += "# 고용노동부 '화학물질 및 물리적 인자의 노출기준' 전체 원본 데이터 DB\n"
out += "# RAG 챗봇 및 비고(특이사항) 추출을 위해 8가지 속성 데이터를 모두 보존합니다.\n\n"
out += "EXPOSURE_LIMITS_DB = {\n"
for k, v in full_db.items():
    out += f'    "{k}": {json.dumps(v, ensure_ascii=False)},\n'
out += "}\n"

with open("exposure_db.py", "w", encoding="utf-8") as f:
    f.write(out)

print(f"🎉 성공! 총 {len(full_db)}개의 데이터가 'exposure_db.py' 파일로 완벽하게 생성되었습니다.")
