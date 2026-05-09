import pdfplumber
import os

def check_pdf_type(file_path):
    """
    PDF 파일 내부에 텍스트 레이어가 존재하는지(TEXT_BASED), 
    순수 스캔본인지(IMAGE_BASED) 판별하는 함수입니다.
    """
    text_content = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            # MSDS의 Section 3은 보통 1~3페이지 내에 존재하므로 앞부분만 검사하여 속도 최적화
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text:
                    text_content += text
                    
        # 의미 있는 텍스트가 일정량(예: 50자) 이상 추출되면 텍스트 기반 PDF로 간주
        if len(text_content.strip()) > 50:
            return "TEXT_BASED"
        else:
            return "IMAGE_BASED"
            
    except Exception as e:
        print(f"파일을 읽는 중 오류 발생: {e}")
        return "ERROR"

# --- 테스트 실행 부분 ---
if __name__ == "__main__":
    # 준비해두신 테스트용 MSDS 파일 이름을 아래에 적어주세요.
    sample_pdf = "/Users/mbp/Desktop/MSDS_Project/PCA005701_DOCU03_a030102 노루페인트.pdf" 
    
    if os.path.exists(sample_pdf):
        print(f"문서 분석 중: {sample_pdf}...")
        result = check_pdf_type(sample_pdf)
        
        print(f"결과: {result}")
        if result == "TEXT_BASED":
            print("✅ Track A 활성화: pdfplumber를 이용한 표(Table) 추출 로직으로 연결합니다.")
        elif result == "IMAGE_BASED":
            print("✅ Track B 활성화: 이미지를 Gemma 모델에 직접 넣어 Vision 처리 로직으로 연결합니다.")
    else:
        print("⚠️ 테스트할 PDF 파일을 찾을 수 없습니다. 경로와 파일명을 확인해 주세요.")



        import pdfplumber

def extract_section3_table(file_path):
    print(f"[{file_path}] 파일에서 표 데이터를 추출합니다...\n")
    
    # 추출된 표 데이터를 담을 리스트
    extracted_data = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            # 보통 Section 3은 1~4페이지 안에 있으므로 앞부분만 탐색합니다.
            for i, page in enumerate(pdf.pages[:4]):
                # 페이지 내의 표(Table) 찾기
                tables = page.extract_tables()
                
                for table in tables:
                    for row in table:
                        # 빈 줄(None)이거나 데이터가 없는 줄은 건너뜀
                        if not row or all(cell is None or cell.strip() == '' for cell in row):
                            continue
                        
                        # 각 칸(Cell)의 줄바꿈(\n)을 띄어쓰기로 바꿔서 깔끔하게 정리
                        clean_row = [cell.replace('\n', ' ').strip() if cell else "" for cell in row]
                        extracted_data.append(clean_row)

        # 결과 출력 (데이터가 잘 뽑혔는지 터미널에서 확인)
        if extracted_data:
            print("✅ 추출된 표 데이터 미리보기:")
            print("-" * 50)
            for row in extracted_data:
                print(row)
            print("-" * 50)
        else:
            print("⚠️ 표 형태의 데이터를 찾지 못했습니다.")
            
        return extracted_data

    except Exception as e:
        print(f"오류 발생: {e}")
        return None

# --- 테스트 실행 부분 ---
if __name__ == "__main__":
    # 아까 'TEXT_BASED'로 잘 나왔던 텍스트형 MSDS 파일의 경로를 적어주세요.
    sample_pdf = "/Users/mbp/Desktop/MSDS_Project/PCA005701_DOCU03_a030102 노루페인트.pdf" 
    
    extract_section3_table(sample_pdf)