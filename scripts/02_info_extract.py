"""
=============================================================
02_info_extract.py - Sarcopenia DCP 논문 정보 추출 (Claude AI)
=============================================================
용도: 각 논문/특허 텍스트에서 타겟/화합물/기전을 Claude AI로 자동 추출
실행: python 02_info_extract.py [--append]

사전 준비:
  1. Claude API 키 필요 (console.anthropic.com)
  2. pip install anthropic pandas openpyxl
  3. 01_pdf_extract.py 먼저 실행

소요 시간: 약 8-16시간 (3,894건 기준)
비용: 약 $60-150 (Claude API)
=============================================================
"""

import os
import sys
import json
import time
import argparse

# ─── Windows 인코딩 문제 해결 ─────────────────────────────
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    # Windows cp949/ascii 강제 우회
    import locale
    try:
        locale.setlocale(locale.LC_ALL, '')
    except Exception:
        pass

# ─── CLI 인자 파싱 ─────────────────────────────────────────
parser = argparse.ArgumentParser(description="근감소증 논문 정보 추출 (Claude AI)")
parser.add_argument("--append", action="store_true",
                    help="APPEND 모드: 기존 Excel에 새 결과만 추가")
_args, _ = parser.parse_known_args()

# ─── 설정 ────────────────────────────────────────────────
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT_FOLDER = os.path.join(BASE_FOLDER, "txt_추출결과")
NEW_PAPERS_TXT = os.path.join(BASE_FOLDER, "new_papers_txt")

RESULT_EXCEL = os.path.join(BASE_FOLDER, "Sarcopenia_문헌분류_결과.xlsx")
RESULT_EXCEL_MAIN = os.path.join(BASE_FOLDER, "Sarcopenia_data.xlsx")
PROGRESS_FILE = os.path.join(BASE_FOLDER, "scripts", "_진행상황.json")
PROCESSED_FILES_LOG = os.path.join(BASE_FOLDER, "processed_files.json")

APPEND_MODE = _args.append or os.environ.get("APPEND_MODE", "false").lower() == "true"
# ─────────────────────────────────────────────────────────

# 근감소증 특화 프롬프트
EXTRACTION_PROMPT = """You are an expert in Sarcopenia drug development and muscle biology.
Read the paper/patent text below, and extract the following information in JSON format.

Items to extract:
1. document_type: "Paper" or "Patent" or "Review" or "Other"
2. study_type: "Clinical" or "Preclinical" or "In vitro" or "In silico" or "Review" or "Patent" or "Epidemiology" or "Biomarker"
3. targets: list of drug targets (e.g. ["Myostatin/GDF-8", "ActRIIB", "mTOR", "AMPK", "MuRF1", "FoxO3", "RIPK3", "IGF-1R"])
4. compounds: list of compound/drug names (e.g. ["Bimagrumab", "Enobosarm", "Testosterone", "HMB", "Leucine", "Metformin"])
5. mechanism_of_action: key mechanism description (1-2 sentences, in Korean)
6. pathways: related signaling pathways (e.g. ["Myostatin/ActRII", "IGF-1/PI3K/Akt/mTOR", "AMPK/PGC-1α", "NF-κB", "Wnt/β-catenin", "Ubiquitin-proteasome", "Autophagy-lysosome", "Gut-muscle axis", "Ferroptosis", "Necroptosis"])
7. cell_types: cell lines, animal models, or human cohorts (e.g. ["C2C12 myotubes", "SAMP8 mouse", "mdx mouse", "DEX-induced atrophy", "Elderly cohort"])
8. key_findings: key findings (1-3 sentences, in Korean)
9. biomarkers: biomarkers for diagnosis/prognosis/treatment response (e.g. ["Grip strength", "SPPB", "ASM/height²", "GDF-15", "CAF", "Irisin", "IL-6", "TNF-α"])
10. relevance_score: relevance to sarcopenia drug development / novel target & biomarker discovery (1-5, 5=highly relevant)
11. therapeutic_category: "Small molecule" or "Biologic" or "Natural product" or "Peptide" or "Gene therapy" or "Cell therapy" or "Probiotic" or "Nutritional" or "Device" or "Combination" or "Diagnostic" or "Other"
12. disease_subtype: specific sarcopenia subtype (e.g. "Age-related", "Cancer cachexia", "Drug-induced", "Sarcopenic obesity", "Neurogenic", "Disuse", "Diabetic")

Respond ONLY with valid JSON. Do not include any other text.
For unknown items, use empty list [] or empty string "".

---
Paper/Patent text:
{text}
"""


def extract_info(client, text, filename):
    """하나의 논문 텍스트에서 정보를 추출"""
    max_chars = 15000
    if len(text) > max_chars:
        text = text[:10000] + "\n...(truncated)...\n" + text[-5000:]

    # 텍스트에서 비정상 문자 제거 (서로게이트 등)
    text = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')

    try:
        prompt_text = EXTRACTION_PROMPT.format(text=text)

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt_text}
            ]
        )
        response_text = message.content[0].text.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        result = json.loads(response_text)
        result["filename"] = filename
        result["status"] = "OK"
        return result

    except json.JSONDecodeError:
        return {"filename": filename, "status": "JSON parse failed", "raw": response_text[:200]}
    except Exception as e:
        err_msg = str(e).encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        return {"filename": filename, "status": f"Error: {err_msg[:100]}"}


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed": [], "results": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def _results_to_dataframe(results):
    import pandas as pd
    rows = []
    for r in results:
        rows.append({
            "파일명": r.get("filename", ""),
            "문서유형": r.get("document_type", ""),
            "연구유형": r.get("study_type", ""),
            "타겟(Target)": ", ".join(r.get("targets", [])) if isinstance(r.get("targets"), list) else str(r.get("targets", "")),
            "화합물(Compound)": ", ".join(r.get("compounds", [])) if isinstance(r.get("compounds"), list) else str(r.get("compounds", "")),
            "기전(MoA)": r.get("mechanism_of_action", ""),
            "신호전달경로": ", ".join(r.get("pathways", [])) if isinstance(r.get("pathways"), list) else str(r.get("pathways", "")),
            "세포/모델": ", ".join(r.get("cell_types", [])) if isinstance(r.get("cell_types"), list) else str(r.get("cell_types", "")),
            "핵심발견": r.get("key_findings", ""),
            "바이오마커": ", ".join(r.get("biomarkers", [])) if isinstance(r.get("biomarkers"), list) else str(r.get("biomarkers", "")),
            "관련도(1-5)": r.get("relevance_score", ""),
            "치료분류": r.get("therapeutic_category", ""),
            "질환아형": r.get("disease_subtype", ""),
            "처리상태": r.get("status", ""),
        })
    return pd.DataFrame(rows)


def _append_or_overwrite(df_new, excel_path):
    import pandas as pd
    if APPEND_MODE and os.path.exists(excel_path):
        try:
            df_existing = pd.read_excel(excel_path, engine="openpyxl")
            existing_files = set(df_existing["파일명"].tolist())
            df_only_new = df_new[~df_new["파일명"].isin(existing_files)]
            if len(df_only_new) > 0:
                df_merged = pd.concat([df_existing, df_only_new], ignore_index=True)
                df_merged.to_excel(excel_path, index=False, engine="openpyxl")
                print(f"  APPEND: {os.path.basename(excel_path)} — 기존 {len(df_existing)} + 신규 {len(df_only_new)} = {len(df_merged)}")
                return len(df_only_new)
            else:
                print(f"  APPEND: {os.path.basename(excel_path)} — 신규 0건")
                return 0
        except Exception as e:
            print(f"  APPEND 실패, 덮어쓰기: {str(e)[:60]}")
    df_new.to_excel(excel_path, index=False, engine="openpyxl")
    print(f"  저장: {os.path.basename(excel_path)} ({len(df_new)}건)")
    return len(df_new)


def save_to_excel(results):
    df_new = _results_to_dataframe(results)
    _append_or_overwrite(df_new, RESULT_EXCEL)
    if os.path.exists(RESULT_EXCEL_MAIN):
        _append_or_overwrite(df_new, RESULT_EXCEL_MAIN)
    else:
        import shutil
        if os.path.exists(RESULT_EXCEL):
            shutil.copy2(RESULT_EXCEL, RESULT_EXCEL_MAIN)
            print(f"  Sarcopenia_data.xlsx 생성 (복사)")
    _update_processed_files_log(results)


def _update_processed_files_log(results):
    processed_log = []
    if os.path.exists(PROCESSED_FILES_LOG):
        try:
            with open(PROCESSED_FILES_LOG, "r", encoding="utf-8") as f:
                processed_log = json.load(f)
        except Exception:
            processed_log = []

    existing = set(processed_log)
    for r in results:
        fn = r.get("filename", "")
        if fn and fn not in existing:
            processed_log.append(fn)
            existing.add(fn)

    with open(PROCESSED_FILES_LOG, "w", encoding="utf-8") as f:
        json.dump(processed_log, f, ensure_ascii=False, indent=2)


def _find_txt_path(filename):
    for folder in [TXT_FOLDER, NEW_PAPERS_TXT]:
        p = os.path.join(folder, filename)
        if os.path.exists(p):
            return p
    return None


def main():
    if not CLAUDE_API_KEY:
        print("=" * 60)
        print("  ANTHROPIC_API_KEY 환경변수를 설정하세요!")
        print("  $env:ANTHROPIC_API_KEY = 'sk-ant-api03-...'")
        print("=" * 60)
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    # txt 파일 목록 수집
    txt_files = []
    if os.path.isdir(TXT_FOLDER):
        txt_files += sorted([f for f in os.listdir(TXT_FOLDER) if f.endswith('.txt') and not f.startswith('_')])
    if os.path.isdir(NEW_PAPERS_TXT):
        new_txts = sorted([f for f in os.listdir(NEW_PAPERS_TXT) if f.endswith('.txt') and not f.startswith('_')])
        existing_set = set(txt_files)
        new_txts = [f for f in new_txts if f not in existing_set]
        txt_files = txt_files + new_txts
        if new_txts:
            print(f"  new_papers_txt에서 {len(new_txts)}건 추가")

    # APPEND 모드: 처리 완료 파일 스킵
    if APPEND_MODE and os.path.exists(PROCESSED_FILES_LOG):
        try:
            with open(PROCESSED_FILES_LOG, "r", encoding="utf-8") as f:
                already_done = set(json.load(f))
            before = len(txt_files)
            txt_files = [f for f in txt_files if f not in already_done]
            skipped = before - len(txt_files)
            if skipped > 0:
                print(f"  APPEND 모드: {skipped}건 스킵")
        except Exception:
            pass

    total = len(txt_files)

    print("=" * 60)
    print(f"  Sarcopenia DCP - 논문 정보 자동 추출")
    print(f"  총 {total}건 처리 예정")
    print(f"  예상 소요: ~{total * 30 // 3600}h {(total * 30 % 3600) // 60}m")
    print(f"  예상 비용: ~${total * 0.03:.0f}-${total * 0.08:.0f}")
    print(f"  모드: {'APPEND' if APPEND_MODE else 'OVERWRITE'}")
    print("  Ctrl+C 로 중단해도 이어서 실행 가능")
    print("=" * 60)
    print()

    progress = load_progress()
    processed = set(progress["processed"])
    results = progress["results"]

    if processed:
        print(f"  이전 진행: {len(processed)}건 완료")
        print()

    try:
        for i, filename in enumerate(txt_files, 1):
            if filename in processed:
                continue

            txt_path = _find_txt_path(filename)
            if not txt_path:
                continue
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()

            print(f"  [{i}/{total}] {filename[:60]}...", end="", flush=True)

            result = extract_info(client, text, filename)
            results.append(result)
            processed.add(filename)

            print(f" → {result.get('status', '')}")

            if len(processed) % 10 == 0:
                progress["processed"] = list(processed)
                progress["results"] = results
                save_progress(progress)
                save_to_excel(results)
                print(f"      (중간 저장: {len(processed)}/{total}건)")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n  중단됨. 진행 상황 저장 중...")

    # 최종 저장
    progress["processed"] = list(processed)
    progress["results"] = results
    save_progress(progress)

    if results:
        save_to_excel(results)

    print()
    print("=" * 60)
    print(f"  완료! 총 {len(processed)}건 처리")
    print(f"  결과: {RESULT_EXCEL_MAIN}")
    print("  다음: python 03_compound_structure.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
