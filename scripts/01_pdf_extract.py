"""
=============================================================
01_pdf_extract.py - Sarcopenia DCP PDF 텍스트 추출
=============================================================
용도: 근감소증 논문/특허 PDF에서 텍스트를 자동 추출
실행: python 01_pdf_extract.py

실행하면:
  - 'txt_추출결과' 폴더가 자동 생성됩니다
  - 각 PDF의 텍스트가 .txt 파일로 저장됩니다
  - totalpaper/papers/, totalpaper/patents/, 상위폴더 모두 탐색

소요 시간: 약 30분-1시간 (3,894건 기준)
=============================================================
"""

import os
import sys
import time

# ─── 설정 ────────────────────────────────────────────────
BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FOLDER = os.path.join(BASE_FOLDER, "txt_추출결과")

# PDF 탐색 경로들
PDF_SEARCH_DIRS = [
    os.path.join(BASE_FOLDER, "totalpaper", "papers"),
    os.path.join(BASE_FOLDER, "totalpaper", "patents"),
    os.path.join(BASE_FOLDER, "totalpaper"),
    os.path.dirname(BASE_FOLDER),  # 상위 폴더 (현재 PDF가 있는 곳)
]
# ─────────────────────────────────────────────────────────


def find_all_pdfs():
    """여러 경로에서 PDF 파일을 수집 (중복 제거)"""
    seen = set()
    pdf_list = []
    for d in PDF_SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith('.pdf') and f not in seen:
                seen.add(f)
                pdf_list.append((f, os.path.join(d, f)))
    return pdf_list


def main():
    try:
        import pdfplumber
    except ImportError:
        print("pdfplumber가 설치되지 않았습니다!")
        print("  pip install pdfplumber")
        sys.exit(1)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_files = find_all_pdfs()
    total = len(pdf_files)

    print("=" * 60)
    print(f"  Sarcopenia DCP - PDF 텍스트 추출 시작")
    print(f"  총 {total}건의 PDF를 처리합니다")
    print("=" * 60)
    print()

    success = 0
    failed = []
    skipped = 0
    start_time = time.time()

    for i, (filename, pdf_path) in enumerate(pdf_files, 1):
        txt_filename = os.path.splitext(filename)[0] + ".txt"
        txt_path = os.path.join(OUTPUT_FOLDER, txt_filename)

        # 이미 처리된 파일은 건너뜀
        if os.path.exists(txt_path):
            skipped += 1
            success += 1
            if skipped <= 5 or skipped % 100 == 0:
                print(f"  [{i}/{total}] 이미 처리됨: {filename[:60]}...")
            continue

        try:
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            full_text = "\n\n".join(text_parts)

            if len(full_text.strip()) < 100:
                failed.append((filename, "텍스트가 거의 없음 (이미지 PDF일 수 있음)"))
                continue

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            success += 1
            elapsed = time.time() - start_time
            avg_time = elapsed / (i - skipped) if (i - skipped) > 0 else 0
            remaining = avg_time * (total - i)
            mins = int(remaining // 60)
            print(f"  [{i}/{total}] 완료: {filename[:60]}... (남은시간: ~{mins}분)")

        except Exception as e:
            failed.append((filename, str(e)[:100]))
            print(f"  [{i}/{total}] 실패: {filename[:60]}... ({str(e)[:50]})")

    # 결과 요약
    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"  처리 완료!")
    print(f"  성공: {success}건 / 실패: {len(failed)}건 / 전체: {total}건")
    print(f"  소요 시간: {int(elapsed//60)}분 {int(elapsed%60)}초")
    print(f"  결과 폴더: {OUTPUT_FOLDER}")
    print("=" * 60)

    if failed:
        fail_path = os.path.join(OUTPUT_FOLDER, "_실패목록.txt")
        with open(fail_path, "w", encoding="utf-8") as f:
            f.write("PDF 텍스트 추출 실패 목록\n")
            f.write("=" * 60 + "\n\n")
            for fname, reason in failed:
                f.write(f"파일: {fname}\n이유: {reason}\n\n")
        print(f"\n  실패 목록: {fail_path}")

    print("\n  다음 단계: python 02_info_extract.py 를 실행하세요.")


if __name__ == "__main__":
    main()
