"""
=============================================================
08_orchestrator.py - 통합 파이프라인 자동 실행
=============================================================
용도: 01~12 모든 단계를 자동으로 순차 실행
실행: python 08_orchestrator.py [--weekly]

--weekly: 패턴분석 + 신약후보 도출까지 포함
기본: 수집 + 추출 + 분석 (일일 모드)
=============================================================
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'
os.environ['APPEND_MODE'] = 'true'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(BASE_FOLDER, "pipeline_status.json")

parser = argparse.ArgumentParser()
parser.add_argument("--weekly", action="store_true", help="주간 전체 분석 모드")
_args, _ = parser.parse_known_args()


def update_status(step, status, detail=""):
    pipeline_status = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                pipeline_status = json.load(f)
        except Exception:
            pass

    pipeline_status["current_step"] = step
    pipeline_status["overall_status"] = status
    pipeline_status["last_update"] = datetime.now().isoformat()
    if detail:
        pipeline_status["detail"] = detail

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(pipeline_status, f, ensure_ascii=False, indent=2)


def run_step(script_name, description, extra_args=None):
    """단계별 스크립트 실행"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"  ⚠ {script_name} 파일 없음 — 스킵")
        return True

    print(f"\n{'='*60}")
    print(f"  ▶ {description}")
    print(f"    스크립트: {script_name}")
    print(f"    시작: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

    update_status(script_name, "running", description)

    cmd = [sys.executable, script_path]
    if extra_args:
        cmd.extend(extra_args)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=SCRIPTS_DIR,
            capture_output=False,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=7200,  # 2시간 타임아웃
        )
        elapsed = time.time() - start
        success = result.returncode == 0

        if success:
            print(f"  ✅ 완료 ({int(elapsed)}초)")
            update_status(script_name, "completed", f"{int(elapsed)}초 소요")
        else:
            print(f"  ❌ 실패 (returncode={result.returncode})")
            update_status(script_name, "error", f"returncode={result.returncode}")

        return success

    except subprocess.TimeoutExpired:
        print(f"  ⏰ 타임아웃 (2시간 초과)")
        update_status(script_name, "timeout")
        return False
    except Exception as e:
        print(f"  ❌ 오류: {str(e)[:100]}")
        update_status(script_name, "error", str(e)[:100])
        return False


def main():
    print("=" * 60)
    print(f"  Sarcopenia DCP - 파이프라인 오케스트레이터")
    print(f"  모드: {'주간 전체 분석' if _args.weekly else '일일 업데이트'}")
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    update_status("start", "running", "파이프라인 시작")

    steps = [
        # Step 1: 신규 논문/특허 수집
        ("05_pubmed_collect.py", "PubMed 신규 논문 수집", ["--years", "1"]),
        ("06_patent_collect.py", "특허 수집", None),
        ("07_biorxiv_collect.py", "bioRxiv/medRxiv 프리프린트 수집", None),

        # Step 2: 텍스트 추출
        ("01_pdf_extract.py", "PDF 텍스트 추출", None),

        # Step 3: AI 정보 추출 (APPEND 모드)
        ("02_info_extract.py", "Claude AI 정보 추출 (APPEND)", ["--append"]),

        # Step 4: 화합물/천연물 구조
        ("03_compound_structure.py", "PubChem 화합물 구조 수집", None),
        ("04_natural_products.py", "천연물 활성성분 매핑", None),

        # Step 5: 바이오마커 분석
        ("12_biomarker_analysis.py", "바이오마커 분석", None),
    ]

    if _args.weekly:
        steps.extend([
            # Step 6: 패턴 분석 + 신약 후보 (주간)
            ("10_pattern_analysis.py", "Dark Target 발굴 (패턴 분석)", None),
            ("11_drug_candidates.py", "AI 신약 후보 도출", None),
        ])

    success_count = 0
    total_steps = len(steps)

    for script, desc, args in steps:
        success = run_step(script, desc, args)
        if success:
            success_count += 1

    # 완료
    print(f"\n{'='*60}")
    print(f"  파이프라인 완료!")
    print(f"  성공: {success_count}/{total_steps} 단계")
    print(f"  종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    update_status("complete", "completed" if success_count == total_steps else "partial",
                  f"{success_count}/{total_steps} 성공")


if __name__ == "__main__":
    main()
