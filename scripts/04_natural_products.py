"""
=============================================================
04_natural_products.py - 천연물 활성성분 매핑
=============================================================
용도: 근감소증 관련 천연물에서 활성 성분을 PubChem으로 매핑
실행: python 04_natural_products.py
소요: ~10분 (무료)
=============================================================
"""

import os
import sys
import json
import time

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_NAMES = ["Sarcopenia_data.xlsx", "Sarcopenia_문헌분류_결과.xlsx"]
OUTPUT_FILE = os.path.join(BASE_FOLDER, "natural_product_actives.json")

# 근감소증 관련 천연물 → 알려진 활성성분 매핑
KNOWN_NP_ACTIVES = {
    "Ursolic acid": ["Ursolic acid"],
    "Tomatidine": ["Tomatidine"],
    "Curcumin": ["Curcumin", "Demethoxycurcumin", "Bisdemethoxycurcumin"],
    "Resveratrol": ["Resveratrol", "trans-Resveratrol"],
    "Leucine": ["L-Leucine"],
    "HMB": ["beta-Hydroxy beta-methylbutyric acid"],
    "Creatine": ["Creatine", "Creatine monohydrate"],
    "Vitamin D": ["Cholecalciferol", "Ergocalciferol", "Calcitriol"],
    "Omega-3": ["Eicosapentaenoic acid", "Docosahexaenoic acid"],
    "Green tea": ["Epigallocatechin gallate", "Epicatechin", "Catechin"],
    "Ginsenoside": ["Ginsenoside Rg1", "Ginsenoside Rb1", "Ginsenoside Rg3"],
    "Berberine": ["Berberine"],
    "Quercetin": ["Quercetin"],
    "Astragalus": ["Astragaloside IV", "Cycloastragenol"],
    "Icariin": ["Icariin"],
    "Whey protein": ["L-Leucine", "beta-Lactoglobulin"],
    "Aronia": ["Cyanidin-3-galactoside", "Chlorogenic acid"],
    "Houttuynia cordata": ["Decanoyl acetaldehyde", "Quercetin"],
    "Silk peptide": ["Glycine", "L-Alanine", "L-Serine"],
    "Chaga mushroom": ["Betulinic acid", "Inotodiol"],
    "Angelica keiskei": ["4-Hydroxyderricin", "Xanthoangelol"],
}


def find_excel():
    for name in EXCEL_NAMES:
        path = os.path.join(BASE_FOLDER, name)
        if os.path.exists(path):
            return path
    return None


def query_pubchem_compound(name):
    """PubChem에서 화합물 정보 조회"""
    import requests
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    try:
        search_url = f"{base_url}/compound/name/{requests.utils.quote(name)}/property/MolecularFormula,MolecularWeight,IsomericSMILES,IUPACName/JSON"
        resp = requests.get(search_url, timeout=15)
        if resp.status_code == 200:
            props = resp.json().get("PropertyTable", {}).get("Properties", [{}])[0]
            cid = props.get("CID", "")
            return {
                "name": name,
                "status": "found",
                "CID": cid,
                "MolecularFormula": props.get("MolecularFormula", ""),
                "MolecularWeight": props.get("MolecularWeight", ""),
                "SMILES": props.get("IsomericSMILES", ""),
                "IUPACName": props.get("IUPACName", ""),
                "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else "",
                "image_url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG?record_type=2d&image_size=300x300" if cid else "",
            }
        return {"name": name, "status": "not_found"}
    except Exception as e:
        return {"name": name, "status": f"error: {str(e)[:50]}"}


def main():
    try:
        import requests
        import pandas as pd
    except ImportError:
        print("pip install requests pandas")
        sys.exit(1)

    # 엑셀에서 천연물/영양소 추출
    excel_path = find_excel()
    detected_nps = set()

    if excel_path:
        df = pd.read_excel(excel_path, engine="openpyxl")
        col = "화합물(Compound)"
        if col in df.columns:
            for val in df[col].dropna():
                for c in str(val).split(","):
                    c = c.strip()
                    if c in KNOWN_NP_ACTIVES:
                        detected_nps.add(c)

        # 치료분류가 Natural product 또는 Nutritional인 것도 추가
        cat_col = "치료분류"
        if cat_col in df.columns:
            mask = df[cat_col].isin(["Natural product", "Nutritional", "Probiotic"])
            for val in df.loc[mask, col].dropna():
                for c in str(val).split(","):
                    c = c.strip()
                    if len(c) > 2:
                        detected_nps.add(c)

    # KNOWN_NP_ACTIVES의 모든 천연물도 포함
    all_nps = set(KNOWN_NP_ACTIVES.keys()) | detected_nps

    print("=" * 60)
    print(f"  Sarcopenia DCP - 천연물 활성성분 매핑")
    print(f"  천연물: {len(all_nps)}개")
    print("=" * 60)
    print()

    # 활성 성분 PubChem 조회
    active_compounds = {}
    all_actives = set()
    for np_name in sorted(all_nps):
        actives = KNOWN_NP_ACTIVES.get(np_name, [])
        for a in actives:
            all_actives.add(a)

    print(f"  총 {len(all_actives)}개 활성 성분 조회 중...")
    for i, act_name in enumerate(sorted(all_actives), 1):
        print(f"  [{i}/{len(all_actives)}] {act_name}...", end="", flush=True)
        result = query_pubchem_compound(act_name)
        active_compounds[act_name] = result
        print(f" → {result['status']}")
        time.sleep(0.3)

    # 결과 저장
    output = {
        "metadata": {
            "version": "1.0",
            "generated_date": time.strftime("%Y-%m-%d"),
            "disease": "Sarcopenia",
            "total_natural_products": len(all_nps),
            "total_active_compounds": len(all_actives),
        },
        "natural_product_mapping": {
            np_name: KNOWN_NP_ACTIVES.get(np_name, [])
            for np_name in sorted(all_nps)
        },
        "active_compounds": active_compounds,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    found = sum(1 for v in active_compounds.values() if v["status"] == "found")
    print()
    print(f"  완료! {found}/{len(all_actives)}개 활성 성분 구조 수집")
    print(f"  결과: {OUTPUT_FILE}")

    # Excel 저장
    try:
        xlsx_path = os.path.join(BASE_FOLDER, "Sarcopenia_천연물_활성성분.xlsx")
        rows = []
        for np_name in sorted(all_nps):
            actives = KNOWN_NP_ACTIVES.get(np_name, [])
            for act in actives:
                info = active_compounds.get(act, {})
                rows.append({
                    "천연물": np_name,
                    "활성성분": act,
                    "분자식": info.get("MolecularFormula", ""),
                    "분자량": info.get("MolecularWeight", ""),
                    "SMILES": info.get("SMILES", ""),
                    "PubChem_CID": info.get("CID", ""),
                })
        pd.DataFrame(rows).to_excel(xlsx_path, index=False, engine="openpyxl")
        print(f"  Excel: {xlsx_path}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
