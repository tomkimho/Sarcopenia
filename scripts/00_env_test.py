"""
=============================================================
00_env_test.py - Sarcopenia DCP 환경 테스트
=============================================================
용도: Python과 필수 라이브러리가 제대로 설치되었는지 확인
실행: python 00_env_test.py
=============================================================
"""

import sys

print("=" * 60)
print("  Sarcopenia Drug Discovery Platform - 환경 테스트")
print("=" * 60)
print()

# 1. Python 버전 확인
print(f"[1] Python 버전: {sys.version}")
if sys.version_info >= (3, 9):
    print("    → OK! Python 3.9 이상입니다.")
else:
    print("    → 경고: Python 3.9 이상을 권장합니다.")
print()

# 2. 필수 라이브러리 확인
libraries = {
    "pandas": "데이터를 엑셀처럼 다루는 도구",
    "openpyxl": "엑셀 파일을 만드는 도구",
    "pdfplumber": "PDF에서 텍스트를 뽑는 도구",
}

print("[2] 필수 라이브러리 확인:")
missing = []
for lib, desc in libraries.items():
    try:
        __import__(lib)
        print(f"    {lib}: OK  ({desc})")
    except ImportError:
        print(f"    {lib}: 미설치!  ({desc})")
        missing.append(lib)
print()

# 3. 선택 라이브러리 확인
optional = {
    "anthropic": "Claude AI API (정보 추출용)",
    "streamlit": "웹 대시보드 (09_website.py 용)",
    "plotly": "인터랙티브 차트 (09_website.py 용)",
    "requests": "PubMed/PubChem API 호출",
}

print("[3] 선택 라이브러리 확인 (나중 설치 가능):")
for lib, desc in optional.items():
    try:
        __import__(lib)
        print(f"    {lib}: OK  ({desc})")
    except ImportError:
        print(f"    {lib}: 미설치  ({desc}) ← 필요 시 설치")
print()

# 4. PDF 폴더 확인
import os
base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
totalpaper = os.path.join(base_folder, "totalpaper")
papers_dir = os.path.join(totalpaper, "papers")
patents_dir = os.path.join(totalpaper, "patents")

# 상위 폴더에서 PDF 직접 확인
parent_pdf_count = 0
parent_dir = os.path.dirname(base_folder)
if os.path.isdir(parent_dir):
    parent_pdf_count = len([f for f in os.listdir(parent_dir) if f.lower().endswith('.pdf')])

paper_count = len([f for f in os.listdir(papers_dir) if f.lower().endswith('.pdf')]) if os.path.isdir(papers_dir) else 0
patent_count = len([f for f in os.listdir(patents_dir) if f.lower().endswith('.pdf')]) if os.path.isdir(patents_dir) else 0

print(f"[4] PDF 파일 확인:")
print(f"    프로젝트 폴더: {base_folder}")
if parent_pdf_count > 0:
    print(f"    상위 폴더 PDF: {parent_pdf_count}개 (이동 필요)")
print(f"    논문 (papers/): {paper_count}개")
print(f"    특허 (patents/): {patent_count}개")
print(f"    총 PDF: {paper_count + patent_count}개")
print()

# 5. 결과 요약
print("=" * 60)
if missing:
    print("  아직 설치 안 된 라이브러리가 있습니다!")
    print(f"  아래 명령어를 실행하세요:")
    print(f"  pip install {' '.join(missing)}")
else:
    print("  모든 필수 라이브러리가 설치되어 있습니다!")
    if paper_count + patent_count == 0 and parent_pdf_count > 0:
        print(f"\n  ⚠️ PDF 파일이 상위 폴더에 {parent_pdf_count}개 있습니다.")
        print("  논문/특허를 totalpaper/papers/ 또는 totalpaper/patents/ 에 분류하거나,")
        print("  01_pdf_extract.py가 상위 폴더에서 자동 탐색합니다.")
    print("\n  다음 단계: python 01_pdf_extract.py 를 실행하세요.")
print("=" * 60)
