# cas_db.py

"""
산업안전보건법 시행규칙 [별표 21] 작업환경측정 대상, [별표 22] 특수건강진단 대상
전체 대상 물질 통합 데이터베이스 (Total CAS DB)
WE: 작업환경측정 (Work Environment)
SH: 특수건강진단 (Special Health)
threshold: 법적 함유량 기준 (%)
"""

LEGAL_CAS_DB = {
    # ==========================================
    # 1. 유기화합물 (Organic Compounds)
    # ==========================================
    "111-30-8": {"name": "글루타르알데히드", "WE": "O", "SH": "O", "threshold": 1.0},
    "55-63-0": {"name": "니트로글리세린", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-52-5": {"name": "니트로메탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "98-95-3": {"name": "니트로벤젠", "WE": "O", "SH": "O", "threshold": 1.0},
    "100-01-6": {"name": "p-니트로아닐린", "WE": "O", "SH": "O", "threshold": 1.0},
    "100-00-5": {"name": "p-니트로클로로벤젠", "WE": "O", "SH": "O", "threshold": 1.0},
    "25321-14-6": {"name": "디니트로톨루엔", "WE": "O", "SH": "O", "threshold": 1.0},
    "121-69-7": {"name": "N,N-디메틸아닐린", "WE": "O", "SH": "O", "threshold": 1.0},
    "124-40-3": {"name": "디메틸아민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "127-19-5": {"name": "N,N-디메틸아세트아미드", "WE": "O", "SH": "O", "threshold": 1.0},
    "68-12-2": {"name": "디메틸포름아미드", "WE": "O", "SH": "O", "threshold": 1.0},
    "111-42-2": {"name": "디에탄올아민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "60-29-7": {"name": "디에틸 에테르", "WE": "O", "SH": "O", "threshold": 1.0},
    "111-40-0": {"name": "디에틸렌트리아민", "WE": "O", "SH": "O", "threshold": 1.0},
    "100-37-8": {"name": "2-디에틸아미노에탄올", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "109-89-7": {"name": "디에틸아민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "123-91-1": {"name": "1,4-디옥산", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-83-8": {"name": "디이소부틸케톤", "WE": "O", "SH": "O", "threshold": 1.0},
    "1717-00-6": {"name": "1,1-디클로로-1-플루오로에탄", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "75-09-2": {"name": "디클로로메탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "95-50-1": {"name": "o-디클로로벤젠", "WE": "O", "SH": "O", "threshold": 1.0},
    "107-06-2": {"name": "1,2-디클로로에탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "540-59-0": {"name": "1,2-디클로로에틸렌", "WE": "O", "SH": "O", "threshold": 1.0},
    "78-87-5": {"name": "1,2-디클로로프로판", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-43-4": {"name": "디클로로플루오로메탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "123-31-9": {"name": "p-디히드록시벤젠", "WE": "O", "SH": "O", "threshold": 1.0},
    "67-56-1": {"name": "메탄올", "WE": "O", "SH": "O", "threshold": 1.0},
    "109-86-4": {"name": "2-메톡시에탄올", "WE": "O", "SH": "O", "threshold": 1.0},
    "110-49-6": {"name": "2-메톡시에틸 아세테이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "591-78-6": {"name": "메틸 n-부틸 케톤", "WE": "O", "SH": "O", "threshold": 1.0},
    "110-43-0": {"name": "메틸 n-아밀 케톤", "WE": "O", "SH": "O", "threshold": 1.0},
    "74-89-5": {"name": "메틸 아민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "79-20-9": {"name": "메틸 아세테이트", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "78-93-3": {"name": "메틸 에틸 케톤", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-10-1": {"name": "메틸 이소부틸 케톤", "WE": "O", "SH": "O", "threshold": 1.0},
    "74-87-3": {"name": "메틸 클로라이드", "WE": "O", "SH": "O", "threshold": 1.0},
    "71-55-6": {"name": "메틸 클로로포름", "WE": "O", "SH": "O", "threshold": 1.0},
    "101-68-8": {"name": "메틸렌 비스(페닐 이소시아네이트)", "WE": "O", "SH": "O", "threshold": 1.0},
    "583-60-8": {"name": "o-메틸시클로헥사논", "WE": "O", "SH": "O", "threshold": 1.0},
    "25639-42-3": {"name": "메틸시클로헥사놀", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-31-6": {"name": "무수 말레산", "WE": "O", "SH": "O", "threshold": 1.0},
    "85-44-9": {"name": "무수 프탈산", "WE": "O", "SH": "O", "threshold": 1.0},
    "71-43-2": {"name": "벤젠", "WE": "O", "SH": "O", "threshold": 1.0},
    "106-99-0": {"name": "1,3-부타디엔", "WE": "O", "SH": "O", "threshold": 1.0},
    "71-36-3": {"name": "n-부탄올", "WE": "O", "SH": "O", "threshold": 1.0},
    "78-92-2": {"name": "2-부탄올", "WE": "O", "SH": "O", "threshold": 1.0},
    "111-76-2": {"name": "2-부톡시에탄올", "WE": "O", "SH": "O", "threshold": 1.0},
    "112-07-2": {"name": "2-부톡시에틸 아세테이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "123-86-4": {"name": "n-부틸 아세테이트", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "106-94-5": {"name": "1-브로모프로판", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-26-3": {"name": "2-브로모프로판", "WE": "O", "SH": "O", "threshold": 1.0},
    "74-83-9": {"name": "브롬화 메틸", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-05-4": {"name": "비닐 아세테이트", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "56-23-5": {"name": "사염화탄소", "WE": "O", "SH": "O", "threshold": 1.0},
    "8052-41-3": {"name": "스토다드 솔벤트", "WE": "O", "SH": "O", "threshold": 1.0},
    "100-42-5": {"name": "스티렌", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-94-1": {"name": "시클로헥사논", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-93-0": {"name": "시클로헥사놀", "WE": "O", "SH": "O", "threshold": 1.0},
    "110-82-7": {"name": "시클로헥산", "WE": "O", "SH": "O", "threshold": 1.0},
    "110-83-8": {"name": "시클로헥센", "WE": "O", "SH": "O", "threshold": 1.0},
    "62-53-3": {"name": "아닐린 및 그 동족체", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-05-8": {"name": "아세토니트릴", "WE": "O", "SH": "O", "threshold": 1.0},
    "67-64-1": {"name": "아세톤", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-07-0": {"name": "아세트알데히드", "WE": "O", "SH": "O", "threshold": 1.0},
    "107-13-1": {"name": "아크릴로니트릴", "WE": "O", "SH": "O", "threshold": 1.0},
    "79-06-1": {"name": "아크릴아미드", "WE": "O", "SH": "O", "threshold": 1.0},
    "106-92-3": {"name": "알릴 글리시딜 에테르", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "141-43-5": {"name": "에탄올아민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "110-80-5": {"name": "2-에톡시에탄올", "WE": "O", "SH": "O", "threshold": 1.0},
    "111-15-9": {"name": "2-에톡시에틸 아세테이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "100-41-4": {"name": "에틸 벤젠", "WE": "O", "SH": "O", "threshold": 1.0},
    "141-78-6": {"name": "에틸 아세테이트", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "140-88-5": {"name": "에틸 아크릴레이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "107-21-1": {"name": "에틸렌 글리콜", "WE": "O", "SH": "O", "threshold": 1.0},
    "628-96-6": {"name": "에틸렌 글리콜 디니트레이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "107-07-3": {"name": "에틸렌 클로로히드린", "WE": "O", "SH": "O", "threshold": 1.0},
    "151-56-4": {"name": "에틸렌이민", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-04-7": {"name": "에틸아민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "556-52-5": {"name": "2,3-에폭시-1-프로판올", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-56-9": {"name": "1,2-에폭시프로판", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "106-89-8": {"name": "에피클로로히드린", "WE": "O", "SH": "O", "threshold": 1.0},
    "74-88-4": {"name": "요오드화 메틸", "WE": "O", "SH": "O", "threshold": 1.0},
    "110-19-0": {"name": "이소부틸 아세테이트", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "78-83-1": {"name": "이소부틸 알코올", "WE": "O", "SH": "O", "threshold": 1.0},
    "123-92-2": {"name": "이소아밀 아세테이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "123-51-3": {"name": "이소아밀 알코올", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-21-4": {"name": "이소프로필 아세테이트", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "67-63-0": {"name": "이소프로필 알코올", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-15-0": {"name": "이황화탄소", "WE": "O", "SH": "O", "threshold": 1.0},
    "1319-77-3": {"name": "크레졸", "WE": "O", "SH": "O", "threshold": 1.0},
    "1330-20-7": {"name": "크실렌", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-90-7": {"name": "클로로벤젠", "WE": "O", "SH": "O", "threshold": 1.0},
    "79-34-5": {"name": "1,1,2,2-테트라클로로에탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "109-99-9": {"name": "테트라히드로푸란", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-88-3": {"name": "톨루엔", "WE": "O", "SH": "O", "threshold": 1.0},
    "584-84-9": {"name": "톨루엔-2,4-디이소시아네이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "91-08-7": {"name": "톨루엔-2,6-디이소시아네이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "121-44-8": {"name": "트리에틸아민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "67-66-3": {"name": "트리클로로메탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "79-00-5": {"name": "1,1,2-트리클로로에탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "79-01-6": {"name": "트리클로로에틸렌", "WE": "O", "SH": "O", "threshold": 1.0},
    "96-18-4": {"name": "1,2,3-트리클로로프로판", "WE": "O", "SH": "O", "threshold": 1.0},
    "127-18-4": {"name": "퍼클로로에틸렌", "WE": "O", "SH": "O", "threshold": 1.0},
    "108-95-2": {"name": "페놀", "WE": "O", "SH": "O", "threshold": 1.0},
    "87-86-5": {"name": "펜타클로로페놀", "WE": "O", "SH": "O", "threshold": 1.0},
    "50-00-0": {"name": "포름알데히드", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-55-8": {"name": "프로필렌이민", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "109-60-4": {"name": "n-프로필 아세테이트", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "110-86-1": {"name": "피리딘", "WE": "O", "SH": "O", "threshold": 1.0},
    "822-06-0": {"name": "헥사메틸렌 디이소시아네이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "110-54-3": {"name": "n-헥산", "WE": "O", "SH": "O", "threshold": 1.0},
    "142-82-5": {"name": "n-헵탄", "WE": "O", "SH": "O", "threshold": 1.0},
    "77-78-1": {"name": "황산 디메틸", "WE": "O", "SH": "O", "threshold": 1.0},
    "302-01-2": {"name": "히드라진", "WE": "O", "SH": "O", "threshold": 1.0},
    
    # === SH(특수건강진단)에만 존재하는 유기화합물 ===
    "8006-61-9": {"name": "가솔린", "WE": "X", "SH": "O", "threshold": 1.0},
    "91-59-8": {"name": "β-나프틸아민", "WE": "X", "SH": "O", "threshold": 1.0},
    "60-11-7": {"name": "p-디메틸아미노아조벤젠", "WE": "X", "SH": "O", "threshold": 1.0},
    "569-61-9": {"name": "마젠타", "WE": "X", "SH": "O", "threshold": 1.0},
    "101-14-4": {"name": "4,4'-메틸렌 비스(2-클로로아닐린)", "WE": "X", "SH": "O", "threshold": 1.0},
    "92-87-5": {"name": "벤지딘 및 그 염", "WE": "X", "SH": "O", "threshold": 1.0},
    "542-88-1": {"name": "비스(클로로메틸) 에테르", "WE": "X", "SH": "O", "threshold": 1.0},
    "492-80-8": {"name": "아우라민", "WE": "X", "SH": "O", "threshold": 1.0},
    "53469-21-9": {"name": "염소화비페닐", "WE": "X", "SH": "O", "threshold": 1.0},
    "11097-69-1": {"name": "염소화비페닐", "WE": "X", "SH": "O", "threshold": 1.0},
    "8007-45-2": {"name": "콜타르", "WE": "X", "SH": "O", "threshold": 1.0},
    "107-30-2": {"name": "클로로메틸 메틸 에테르", "WE": "X", "SH": "O", "threshold": 1.0},
    "8006-64-2": {"name": "테레빈유", "WE": "X", "SH": "O", "threshold": 1.0},
    "57-57-8": {"name": "β-프로피오락톤", "WE": "X", "SH": "O", "threshold": 1.0},
    "91-15-6": {"name": "o-프탈로디니트릴", "WE": "X", "SH": "O", "threshold": 1.0},

    # ==========================================
    # 2. 금속류 (Metals)
    # ==========================================
    "7440-50-8": {"name": "구리", "WE": "O", "SH": "O", "threshold": 1.0},
    "7439-92-1": {"name": "납 및 그 무기화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-02-0": {"name": "니켈 및 그 무기화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "13463-39-3": {"name": "니켈 카르보닐", "WE": "O", "SH": "O", "threshold": 1.0},
    "7439-96-5": {"name": "망간 및 그 무기화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "78-00-2": {"name": "사알킬납", "WE": "X", "SH": "O", "threshold": 1.0}, # SH Only
    "7440-39-3": {"name": "바륨 및 그 가용성 화합물", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "7440-06-4": {"name": "백금 및 그 가용성 염", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "1309-48-4": {"name": "산화마그네슘", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "1314-13-2": {"name": "산화아연", "WE": "O", "SH": "O", "threshold": 1.0},
    "1309-37-1": {"name": "산화철", "WE": "O", "SH": "O", "threshold": 1.0},
    "1327-53-3": {"name": "삼산화비소", "WE": "X", "SH": "O", "threshold": 1.0}, # SH Only
    "7782-49-2": {"name": "셀레늄 및 그 화합물", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "7439-97-6": {"name": "수은 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-36-0": {"name": "안티몬 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7429-90-5": {"name": "알루미늄 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "1314-62-1": {"name": "오산화바나듐", "WE": "O", "SH": "O", "threshold": 1.0},
    "7553-56-2": {"name": "요오드 및 요오드화물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-74-6": {"name": "인듐 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-22-4": {"name": "은 및 그 가용성 화합물", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "13463-67-7": {"name": "이산화티타늄", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "7440-31-5": {"name": "주석 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-67-7": {"name": "지르코늄 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-43-9": {"name": "카드뮴 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-48-4": {"name": "코발트", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-47-3": {"name": "크롬 및 그 무기화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-33-7": {"name": "텅스텐 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},

    # ==========================================
    # 3. 산 및 알칼리류 (Acids and Alkalis)
    # ==========================================
    "64-18-6": {"name": "개미산", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "7722-84-1": {"name": "과산화수소", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "108-24-7": {"name": "무수 초산", "WE": "O", "SH": "O", "threshold": 1.0},
    "7664-39-3": {"name": "불화수소", "WE": "O", "SH": "O", "threshold": 1.0},
    "10035-10-6": {"name": "브롬화수소", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "1310-73-2": {"name": "수산화 나트륨", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "1310-58-3": {"name": "수산화 칼륨", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "143-33-9": {"name": "시안화 나트륨", "WE": "O", "SH": "O", "threshold": 1.0},
    "151-50-8": {"name": "시안화 칼륨", "WE": "O", "SH": "O", "threshold": 1.0},
    "592-01-8": {"name": "시안화 칼슘", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "79-10-7": {"name": "아크릴산", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "7647-01-0": {"name": "염화수소", "WE": "O", "SH": "O", "threshold": 1.0},
    "7664-38-2": {"name": "인산", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "7697-37-2": {"name": "질산", "WE": "O", "SH": "O", "threshold": 1.0},
    "64-19-7": {"name": "초산", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "76-03-9": {"name": "트리클로로아세트산", "WE": "O", "SH": "O", "threshold": 1.0},
    "7664-93-9": {"name": "황산", "WE": "O", "SH": "O", "threshold": 1.0},

    # ==========================================
    # 4. 가스 상태 물질류 (Gases)
    # ==========================================
    "7782-41-4": {"name": "불소", "WE": "O", "SH": "O", "threshold": 1.0},
    "7726-95-6": {"name": "브롬", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-21-8": {"name": "산화에틸렌", "WE": "O", "SH": "O", "threshold": 1.0},
    "7784-42-1": {"name": "삼수소화 비소", "WE": "O", "SH": "O", "threshold": 1.0},
    "74-90-8": {"name": "시안화 수소", "WE": "O", "SH": "O", "threshold": 1.0},
    "7664-41-7": {"name": "암모니아", "WE": "O", "SH": "X", "threshold": 1.0}, # WE Only
    "7782-50-5": {"name": "염소", "WE": "O", "SH": "O", "threshold": 1.0},
    "10028-15-6": {"name": "오존", "WE": "O", "SH": "O", "threshold": 1.0},
    "10102-44-0": {"name": "이산화질소", "WE": "O", "SH": "O", "threshold": 1.0},
    "7446-09-5": {"name": "이산화황", "WE": "O", "SH": "O", "threshold": 1.0},
    "10102-43-9": {"name": "일산화질소", "WE": "O", "SH": "O", "threshold": 1.0},
    "630-08-0": {"name": "일산화탄소", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-44-5": {"name": "포스겐", "WE": "O", "SH": "O", "threshold": 1.0},
    "7803-51-2": {"name": "포스핀", "WE": "O", "SH": "O", "threshold": 1.0},
    "7783-06-4": {"name": "황화수소", "WE": "O", "SH": "O", "threshold": 1.0},

    # ==========================================
    # 5. 허가 대상 유해물질 (Permitted Substances)
    # ==========================================
    "134-32-7": {"name": "a-나프틸아민 및 그 염", "WE": "O", "SH": "O", "threshold": 1.0},
    "119-90-4": {"name": "디아니시딘 및 그 염", "WE": "O", "SH": "O", "threshold": 1.0},
    "91-94-1": {"name": "디클로로벤지딘 및 그 염", "WE": "O", "SH": "O", "threshold": 1.0},
    "7440-41-7": {"name": "베릴륨 및 그 화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "98-07-7": {"name": "벤조트리클로라이드", "WE": "O", "SH": "O", "threshold": 0.5}, # 🌟 핵심: 유일한 0.5% 기준 [cite: 200, 406]
    "7440-38-2": {"name": "비소 및 그 무기화합물", "WE": "O", "SH": "O", "threshold": 1.0},
    "75-01-4": {"name": "염화비닐", "WE": "O", "SH": "O", "threshold": 1.0},
    "65996-93-2": {"name": "콜타르피치 휘발물", "WE": "O", "SH": "O", "threshold": 1.0},
    "13530-65-9": {"name": "크롬산 아연", "WE": "O", "SH": "O", "threshold": 1.0},
    "119-93-7": {"name": "o-톨리딘 및 그 염", "WE": "O", "SH": "O", "threshold": 1.0},
    "12035-72-2": {"name": "황화니켈류", "WE": "O", "SH": "O", "threshold": 1.0},
    "16812-54-7": {"name": "황화니켈류", "WE": "O", "SH": "O", "threshold": 1.0},

    # ==========================================
    # 6. 분진류 (Dusts - CAS 번호가 명확히 명시된 것들)
    # ==========================================
    "14808-60-7": {"name": "석영", "WE": "O", "SH": "O", "threshold": 1.0},
    "14464-46-1": {"name": "크리스토발라이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "15468-32-3": {"name": "트리디마이트", "WE": "O", "SH": "O", "threshold": 1.0},
    "14807-96-6": {"name": "소우프스톤/활석", "WE": "O", "SH": "O", "threshold": 1.0},
    "12001-26-2": {"name": "운모", "WE": "O", "SH": "O", "threshold": 1.0},
    "65997-15-1": {"name": "포틀랜드 시멘트", "WE": "O", "SH": "O", "threshold": 1.0},
    "7782-42-5": {"name": "흑연", "WE": "O", "SH": "O", "threshold": 1.0},
    "1332-21-4": {"name": "석면 분진", "WE": "O", "SH": "O", "threshold": 1.0}
}