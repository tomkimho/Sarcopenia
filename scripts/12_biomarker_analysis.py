"""
=============================================================
12_biomarker_analysis.py - 바이오마커 분석
=============================================================
용도: 근감소증 문헌에서 바이오마커를 추출, 분류, 연관성 분석
실행: python 12_biomarker_analysis.py
소요: ~5분 (무료)
=============================================================
"""

import os
import sys
import json
from collections import Counter, defaultdict
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_NAMES = ["Sarcopenia_data.xlsx", "Sarcopenia_문헌분류_결과.xlsx"]
OUTPUT_DIR = os.path.join(BASE_FOLDER, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "biomarker_analysis.json")

# 근감소증 바이오마커 카테고리
BIOMARKER_CATEGORIES = {
    "physical_function": [
        "Grip strength", "SPPB", "Gait speed", "6MWD", "Chair stand",
        "TUG", "400m walk", "Stair climb", "SARC-F", "Balance",
    ],
    "muscle_mass": [
        "ASM", "ASM/height²", "DXA", "BIA", "CT scan", "MRI",
        "Skeletal muscle index", "Lean body mass", "Phase angle",
    ],
    "hormone": [
        "Testosterone", "IGF-1", "GH", "DHEA", "Estradiol",
        "Cortisol", "Insulin", "Leptin", "Adiponectin", "Irisin",
        "Myostatin", "GDF-15", "GDF-8", "Follistatin",
    ],
    "inflammation": [
        "IL-6", "TNF-α", "CRP", "IL-1β", "IL-10", "IL-15",
        "NF-κB", "NLRP3", "IFN-γ", "TGF-β",
    ],
    "muscle_protein_turnover": [
        "MuRF1", "MAFbx", "Atrogin-1", "Myosin heavy chain",
        "Troponin", "Creatine kinase", "3-Methylhistidine",
        "Urinary creatinine", "p70S6K", "4E-BP1",
    ],
    "oxidative_stress": [
        "MDA", "SOD", "GSH", "Gpx4", "8-OHdG", "ROS",
        "Nrf2", "Catalase", "Vitamin E", "CoQ10",
    ],
    "gut_microbiome": [
        "SCFA", "Butyrate", "Faecalibacterium", "Bifidobacterium",
        "Lactobacillus", "Roseburia", "Bacteroides",
        "Firmicutes/Bacteroidetes ratio", "LPS",
    ],
    "neuromuscular": [
        "CAF", "MUNIX", "BDNF", "GDNF", "NMJ",
        "Agrin", "Motor unit", "ETV4", "Acetylcholine",
    ],
    "cell_death": [
        "Caspase-3", "p53", "RIPK3", "MLKL", "GPX4",
        "Ferritin", "Iron", "SLC7A11", "TUNEL",
    ],
}


def find_excel():
    for name in EXCEL_NAMES:
        path = os.path.join(BASE_FOLDER, name)
        if os.path.exists(path):
            return path
    return None


def categorize_biomarker(name):
    """바이오마커 카테고리 분류"""
    name_lower = name.lower()
    for category, markers in BIOMARKER_CATEGORIES.items():
        for marker in markers:
            if marker.lower() in name_lower or name_lower in marker.lower():
                return category
    return "other"


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
    print(f"  Sarcopenia DCP - 바이오마커 분석")
    print(f"  총 문헌: {len(df_ok)}건")
    print("=" * 60)
    print()

    # ── 바이오마커 추출 ──
    biomarker_counter = Counter()
    biomarker_papers = defaultdict(list)
    biomarker_targets = defaultdict(lambda: defaultdict(int))
    biomarker_pathways = defaultdict(lambda: defaultdict(int))

    for idx, row in df_ok.iterrows():
        bm_str = str(row.get("바이오마커", ""))
        if bm_str == "nan":
            continue
        targets = str(row.get("타겟(Target)", ""))
        pathways = str(row.get("신호전달경로", ""))

        for bm in bm_str.split(","):
            bm = bm.strip()
            if len(bm) > 1:
                biomarker_counter[bm] += 1
                biomarker_papers[bm].append(idx)

                # 타겟 연관성
                if targets != "nan":
                    for t in targets.split(","):
                        t = t.strip()
                        if len(t) > 1:
                            biomarker_targets[bm][t] += 1

                # 경로 연관성
                if pathways != "nan":
                    for p in pathways.split(","):
                        p = p.strip()
                        if len(p) > 1:
                            biomarker_pathways[bm][p] += 1

    print(f"  고유 바이오마커: {len(biomarker_counter)}종")

    # ── 카테고리별 분류 ──
    categories = defaultdict(list)
    for bm, count in biomarker_counter.most_common():
        cat = categorize_biomarker(bm)
        categories[cat].append({"name": bm, "count": count})

    for cat, items in categories.items():
        print(f"    {cat}: {len(items)}종")

    # ── Top 바이오마커 ──
    top_biomarkers = [
        {"name": bm, "count": count, "category": categorize_biomarker(bm)}
        for bm, count in biomarker_counter.most_common(50)
    ]

    # ── 바이오마커-타겟 매트릭스 ──
    bm_target_matrix = {}
    for bm in [b["name"] for b in top_biomarkers[:20]]:
        bm_target_matrix[bm] = dict(biomarker_targets.get(bm, {}))

    # ── 바이오마커-경로 매트릭스 ──
    bm_pathway_matrix = {}
    for bm in [b["name"] for b in top_biomarkers[:20]]:
        bm_pathway_matrix[bm] = dict(biomarker_pathways.get(bm, {}))

    # ── 진단 vs 예후 vs 치료반응 분류 (추정) ──
    diagnostic_markers = []
    prognostic_markers = []
    therapeutic_markers = []

    for bm_info in top_biomarkers:
        bm = bm_info["name"]
        cat = bm_info["category"]
        if cat in ("physical_function", "muscle_mass"):
            diagnostic_markers.append(bm)
        elif cat in ("hormone", "inflammation", "cell_death"):
            prognostic_markers.append(bm)
        elif cat in ("muscle_protein_turnover", "gut_microbiome"):
            therapeutic_markers.append(bm)

    # ── 결과 저장 ──
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_biomarkers": len(biomarker_counter),
        "categories": {cat: items for cat, items in categories.items()},
        "top_biomarkers": top_biomarkers,
        "biomarker_target_matrix": bm_target_matrix,
        "biomarker_pathways": bm_pathway_matrix,
        "diagnostic_markers": diagnostic_markers[:10],
        "prognostic_markers": prognostic_markers[:10],
        "therapeutic_markers": therapeutic_markers[:10],
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print(f"  완료!")
    print(f"  결과: {OUTPUT_FILE}")
    print(f"  진단 마커: {len(diagnostic_markers)}개")
    print(f"  예후 마커: {len(prognostic_markers)}개")
    print(f"  치료반응 마커: {len(therapeutic_markers)}개")


if __name__ == "__main__":
    main()
