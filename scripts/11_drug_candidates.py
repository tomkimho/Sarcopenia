"""
=============================================================
11_drug_candidates.py - AI 신약 후보 도출
=============================================================
용도: Dark Target에 대해 Claude AI가 novel compound 후보를 제안
실행: python 11_drug_candidates.py
소요: ~5분 / 비용: ~$0.5
=============================================================
"""

import os
import sys
import json
import time
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_FOLDER, "output")
INTEL_REPORT = os.path.join(OUTPUT_DIR, "intelligence_report.json")
CANDIDATES_FILE = os.path.join(OUTPUT_DIR, "candidate_molecules.json")

CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

CANDIDATE_PROMPT = """You are an expert medicinal chemist specializing in sarcopenia drug development.

Based on the following Dark Target analysis from our literature database, suggest novel drug candidate molecules.

Target: {target}
- Paper count: {paper_count}
- Average relevance: {avg_relevance}/5
- Related pathways: {pathways}
- Known compounds for this target: {compounds}

Requirements:
1. Suggest 2-3 novel compound approaches (can be modifications of known scaffolds or new chemotypes)
2. For each, provide:
   - SMILES string (must be valid)
   - Rationale for design (in Korean)
   - Predicted mechanism of action
   - Novelty score (1-10, 10=completely novel)
   - Key advantages over existing approaches
   - Potential safety concerns

IMPORTANT for sarcopenia drug development:
- Must improve BOTH muscle mass AND physical function (past failures: mass↑ but function unchanged)
- Consider oral bioavailability (elderly patients prefer oral dosing)
- Minimal drug-drug interaction (polypharmacy in elderly)
- Long-term safety profile (chronic use required)
- Consider sarcopenic obesity dual activity

Respond ONLY in valid JSON format:
{{
  "target": "{target}",
  "candidates": [
    {{
      "smiles": "...",
      "rationale": "...",
      "mechanism": "...",
      "novelty_score": 8,
      "advantages": "...",
      "safety_concerns": "...",
      "therapeutic_category": "Small molecule|Biologic|Peptide|Other"
    }}
  ]
}}
"""


def validate_smiles(smiles):
    """간단한 SMILES 유효성 검사"""
    if not smiles or len(smiles) < 3:
        return False
    # 기본 문자 확인
    valid_chars = set("CNOSPFClBrI[]()=#@+-.0123456789/\\cnos")
    return all(c in valid_chars for c in smiles)


def main():
    if not CLAUDE_API_KEY:
        print("ANTHROPIC_API_KEY를 설정하세요.")
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("pip install anthropic")
        sys.exit(1)

    if not os.path.exists(INTEL_REPORT):
        print("intelligence_report.json이 없습니다. 10_pattern_analysis.py를 먼저 실행하세요.")
        sys.exit(1)

    with open(INTEL_REPORT, "r", encoding="utf-8") as f:
        report = json.load(f)

    dark_targets = report.get("top_dark_targets", [])[:100]  # Top 100

    print("=" * 60)
    print(f"  Sarcopenia DCP - AI 신약 후보 도출")
    print(f"  분석 대상: Top {len(dark_targets)} Dark Targets")
    print("=" * 60)
    print()

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    all_candidates = []

    for i, dt in enumerate(dark_targets, 1):
        target = dt["target"]
        print(f"  [{i}/{len(dark_targets)}] {target}...", end="", flush=True)

        prompt = CANDIDATE_PROMPT.format(
            target=target,
            paper_count=dt.get("paper_count", 0),
            avg_relevance=dt.get("avg_relevance", 0),
            pathways=", ".join(dt.get("pathways", [])[:10]),
            compounds=", ".join(dt.get("compounds", [])[:10]) or "None known",
        )

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            result = json.loads(text)
            candidates = result.get("candidates", [])

            # SMILES 검증
            for c in candidates:
                c["target"] = target
                c["validation_status"] = "Valid" if validate_smiles(c.get("smiles", "")) else "Invalid SMILES"

            all_candidates.extend(candidates)
            print(f" → {len(candidates)}개 후보")

        except Exception as e:
            print(f" → 오류: {str(e)[:60]}")

        time.sleep(2)

    # 결과 저장
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_candidates": len(all_candidates),
        "targets_analyzed": len(dark_targets),
        "candidates": all_candidates,
    }

    with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Excel 저장
    try:
        import pandas as pd
        xlsx_path = os.path.join(OUTPUT_DIR, "Sarcopenia_신약후보물질.xlsx")
        if all_candidates:
            pd.DataFrame(all_candidates).to_excel(xlsx_path, index=False, engine="openpyxl")
            print(f"\n  Excel: {xlsx_path}")
    except Exception:
        pass

    valid = sum(1 for c in all_candidates if c.get("validation_status") == "Valid")
    print(f"\n  완료! 총 {len(all_candidates)}개 후보 / 유효 SMILES: {valid}개")
    print(f"  결과: {CANDIDATES_FILE}")


if __name__ == "__main__":
    main()
