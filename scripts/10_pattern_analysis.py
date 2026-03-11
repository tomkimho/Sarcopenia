"""
=============================================================
10_pattern_analysis.py - Dark Target 발굴 (패턴 분석)
=============================================================
용도: 근감소증 문헌 데이터에서 미개척 타겟(Dark Target)을 발굴
      Novelty Index, Gap Analysis, Multi-target Synergy 분석
실행: python 10_pattern_analysis.py
소요: ~5-10분 (무료, 로컬)
=============================================================
"""

import os
import sys
import json
import math
from collections import Counter, defaultdict
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_NAMES = ["Sarcopenia_data.xlsx", "Sarcopenia_문헌분류_결과.xlsx"]
OUTPUT_DIR = os.path.join(BASE_FOLDER, "output")

# 근감소증 타겟 정규화 매핑
TARGET_NORMALIZE = {
    "Myostatin": "Myostatin/GDF-8",
    "GDF-8": "Myostatin/GDF-8",
    "GDF8": "Myostatin/GDF-8",
    "myostatin": "Myostatin/GDF-8",
    "Activin receptor type IIB": "ActRIIB",
    "ActRII": "ActRIIB",
    "ACVR2B": "ActRIIB",
    "mTOR": "mTOR/PI3K/Akt",
    "PI3K/Akt": "mTOR/PI3K/Akt",
    "Akt/mTOR": "mTOR/PI3K/Akt",
    "IGF-1": "IGF-1/IGF-1R",
    "IGF1": "IGF-1/IGF-1R",
    "IGF-1R": "IGF-1/IGF-1R",
    "insulin-like growth factor 1": "IGF-1/IGF-1R",
    "MuRF1": "MuRF1/MAFbx",
    "MAFbx": "MuRF1/MAFbx",
    "Atrogin-1": "MuRF1/MAFbx",
    "FOXO3": "FoxO3",
    "FoxO3a": "FoxO3",
    "FOXO": "FoxO3",
    "AMPK": "AMPK/PGC-1α",
    "PGC-1α": "AMPK/PGC-1α",
    "PGC-1alpha": "AMPK/PGC-1α",
    "RIPK3": "RIPK1/RIPK3",
    "RIPK1": "RIPK1/RIPK3",
    "NF-κB": "NF-κB",
    "NF-kB": "NF-κB",
    "NFkB": "NF-κB",
    "androgen receptor": "Androgen Receptor",
    "AR": "Androgen Receptor",
    "GDF-15": "GDF-15",
    "GDF15": "GDF-15",
}


def normalize_target(name):
    name = name.strip()
    return TARGET_NORMALIZE.get(name, name)


def find_excel():
    for name in EXCEL_NAMES:
        path = os.path.join(BASE_FOLDER, name)
        if os.path.exists(path):
            return path
    return None


def main():
    import pandas as pd

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    excel_path = find_excel()
    if not excel_path:
        print("Sarcopenia_data.xlsx가 없습니다.")
        sys.exit(1)

    df = pd.read_excel(excel_path, engine="openpyxl")
    df["관련도"] = pd.to_numeric(df.get("관련도(1-5)", 0), errors="coerce").fillna(0).astype(int)
    df_ok = df[df["처리상태"].isin(["성공", "OK"])].copy() if "처리상태" in df.columns else df.copy()

    print("=" * 60)
    print(f"  Sarcopenia DCP - Dark Target 발굴")
    print(f"  총 문헌: {len(df_ok)}건")
    print("=" * 60)
    print()

    # ── 1. 타겟 빈도 분석 ──
    target_papers = defaultdict(list)
    for idx, row in df_ok.iterrows():
        targets = str(row.get("타겟(Target)", ""))
        if targets == "nan":
            continue
        for t in targets.split(","):
            t = normalize_target(t)
            if len(t) > 1:
                target_papers[t].append(idx)

    print(f"  고유 타겟: {len(target_papers)}개")

    # ── 2. 타겟-화합물 매트릭스 ──
    target_compound = defaultdict(lambda: defaultdict(int))
    compound_papers = defaultdict(list)
    for idx, row in df_ok.iterrows():
        targets = str(row.get("타겟(Target)", ""))
        compounds = str(row.get("화합물(Compound)", ""))
        if targets == "nan" or compounds == "nan":
            continue
        t_list = [normalize_target(t) for t in targets.split(",") if t.strip()]
        c_list = [c.strip() for c in compounds.split(",") if c.strip()]
        for t in t_list:
            for c in c_list:
                target_compound[t][c] += 1
        for c in c_list:
            compound_papers[c].append(idx)

    # ── 3. Dark Target 발굴 ──
    # Novelty Index = (평균관련도 * 경로다양성) / log(논문수 + 1)
    dark_targets = []
    for target, idxs in target_papers.items():
        if len(target) <= 2:
            continue
        papers = df_ok.loc[df_ok.index.isin(idxs)]
        avg_rel = papers["관련도"].mean()
        paper_count = len(papers)

        # 경로 다양성
        pathways = set()
        for _, row in papers.iterrows():
            pw = str(row.get("신호전달경로", ""))
            if pw != "nan":
                for p in pw.split(","):
                    p = p.strip()
                    if len(p) > 1:
                        pathways.add(p)

        pathway_diversity = len(pathways) / max(paper_count, 1)

        # 관련 화합물
        compounds = list(target_compound.get(target, {}).keys())

        # Novelty Index: 논문이 적고 관련도가 높고 경로가 다양한 타겟
        if paper_count <= 10:
            novelty_index = (avg_rel * (1 + pathway_diversity)) / math.log(paper_count + 2)
        else:
            novelty_index = 0  # 이미 많이 연구된 타겟은 제외

        if novelty_index > 0 and avg_rel >= 3.0:
            dark_targets.append({
                "target": target,
                "novelty_index": novelty_index,
                "paper_count": paper_count,
                "avg_relevance": avg_rel,
                "pathway_diversity": pathway_diversity,
                "pathways": sorted(pathways)[:10],
                "compounds": compounds[:10],
            })

    dark_targets.sort(key=lambda x: x["novelty_index"], reverse=True)
    print(f"  Dark Targets 발굴: {len(dark_targets)}개")

    # ── 4. Gap Analysis ──
    top_targets = sorted(target_papers.keys(), key=lambda x: len(target_papers[x]), reverse=True)[:100]
    top_compounds = sorted(compound_papers.keys(), key=lambda x: len(compound_papers[x]), reverse=True)[:100]

    gaps = []
    for t in top_targets:
        for c in top_compounds:
            if target_compound[t].get(c, 0) == 0:
                t_count = len(target_papers.get(t, []))
                c_count = len(compound_papers.get(c, []))
                gap_score = math.sqrt(t_count * c_count)
                if gap_score > 5:
                    gaps.append({
                        "target": t,
                        "compound": c,
                        "gap_score": gap_score,
                        "target_papers": t_count,
                        "compound_papers": c_count,
                    })

    gaps.sort(key=lambda x: x["gap_score"], reverse=True)
    print(f"  Gap 조합: {len(gaps)}개")

    # ── 5. Multi-target Synergy ──
    target_cooccurrence = defaultdict(int)
    for _, row in df_ok.iterrows():
        targets = str(row.get("타겟(Target)", ""))
        if targets == "nan":
            continue
        t_list = [normalize_target(t) for t in targets.split(",") if t.strip() and len(t.strip()) > 1]
        for i in range(len(t_list)):
            for j in range(i + 1, len(t_list)):
                pair = tuple(sorted([t_list[i], t_list[j]]))
                target_cooccurrence[pair] += 1

    synergies = []
    for (t1, t2), count in target_cooccurrence.items():
        if count >= 3:
            # 공유 경로 계산
            pw1 = set()
            pw2 = set()
            for idx in target_papers.get(t1, []):
                if idx in df_ok.index:
                    pw = str(df_ok.loc[idx].get("신호전달경로", ""))
                    if pw != "nan":
                        for p in pw.split(","):
                            pw1.add(p.strip())
            for idx in target_papers.get(t2, []):
                if idx in df_ok.index:
                    pw = str(df_ok.loc[idx].get("신호전달경로", ""))
                    if pw != "nan":
                        for p in pw.split(","):
                            pw2.add(p.strip())

            shared = pw1 & pw2
            synergy_score = count * (1 + len(shared) * 0.2)
            synergies.append({
                "target1": t1,
                "target2": t2,
                "co_occurrence": count,
                "synergy_score": synergy_score,
                "shared_pathways": sorted(shared)[:5],
            })

    synergies.sort(key=lambda x: x["synergy_score"], reverse=True)
    print(f"  시너지 조합: {len(synergies)}개")

    # ── 결과 저장 ──
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_papers_analyzed": len(df_ok),
        "unique_targets": len(target_papers),
        "unique_compounds": len(compound_papers),
        "dark_targets_count": len(dark_targets),
        "top_dark_targets": dark_targets[:100],
        "top_gaps": gaps[:100],
        "top_synergies": synergies[:100],
        "target_compound_matrix": {t: dict(compounds) for t, compounds in list(target_compound.items())[:100]},
    }

    report_path = os.path.join(OUTPUT_DIR, "intelligence_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Dark Targets Excel
    dt_xlsx = os.path.join(OUTPUT_DIR, "Sarcopenia_Dark_Targets.xlsx")
    pd.DataFrame(dark_targets).to_excel(dt_xlsx, index=False, engine="openpyxl")

    # Gap Analysis Excel
    gap_xlsx = os.path.join(OUTPUT_DIR, "Sarcopenia_Gap_Analysis.xlsx")
    pd.DataFrame(gaps[:100]).to_excel(gap_xlsx, index=False, engine="openpyxl")

    print()
    print(f"  결과 저장:")
    print(f"    {report_path}")
    print(f"    {dt_xlsx}")
    print(f"    {gap_xlsx}")
    print(f"\n  다음: python 11_drug_candidates.py")


if __name__ == "__main__":
    main()
