"""
=============================================================
03_compound_structure.py - PubChem 화합물 구조 수집
=============================================================
용도: 추출된 화합물명으로 PubChem에서 구조 정보를 자동 수집
실행: python 03_compound_structure.py
소요: ~30분 (무료)
=============================================================
"""

import os
import sys
import json
import time
import re

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_NAMES = ["Sarcopenia_data.xlsx", "Sarcopenia_문헌분류_결과.xlsx"]
OUTPUT_FILE = os.path.join(BASE_FOLDER, "compound_structures.json")


def find_excel():
    for name in EXCEL_NAMES:
        path = os.path.join(BASE_FOLDER, name)
        if os.path.exists(path):
            return path
    return None


def get_all_compounds(excel_path):
    """엑셀에서 모든 화합물명을 추출"""
    import pandas as pd
    df = pd.read_excel(excel_path, engine="openpyxl")
    compounds = set()
    col = "화합물(Compound)"
    if col not in df.columns:
        return []
    for val in df[col].dropna():
        for c in str(val).split(","):
            c = c.strip()
            if len(c) > 1 and c.lower() not in ('nan', 'none', 'n/a', '-', ''):
                compounds.add(c)
    return sorted(compounds)


def query_pubchem(compound_name, max_retries=3):
    """PubChem에서 화합물 정보 조회"""
    import requests
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    for attempt in range(max_retries):
        try:
            # 이름으로 CID 검색
            search_url = f"{base_url}/compound/name/{requests.utils.quote(compound_name)}/JSON"
            resp = requests.get(search_url, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                compounds = data.get("PC_Compounds", [])
                if compounds:
                    comp = compounds[0]
                    cid = comp.get("id", {}).get("id", {}).get("cid", "")

                    # 추가 정보 조회
                    props_url = f"{base_url}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IsomericSMILES,IUPACName,InChI/JSON"
                    props_resp = requests.get(props_url, timeout=15)

                    result = {
                        "name": compound_name,
                        "status": "found",
                        "CID": cid,
                        "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                        "image_url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG?record_type=2d&image_size=300x300",
                    }

                    if props_resp.status_code == 200:
                        props = props_resp.json().get("PropertyTable", {}).get("Properties", [{}])[0]
                        result.update({
                            "MolecularFormula": props.get("MolecularFormula", ""),
                            "MolecularWeight": props.get("MolecularWeight", ""),
                            "SMILES": props.get("IsomericSMILES", ""),
                            "IUPACName": props.get("IUPACName", ""),
                            "InChI": props.get("InChI", ""),
                        })

                    return result

            return {"name": compound_name, "status": "not_found"}

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {"name": compound_name, "status": f"error: {str(e)[:50]}"}

    return {"name": compound_name, "status": "not_found"}


def main():
    try:
        import requests
    except ImportError:
        print("pip install requests")
        sys.exit(1)

    excel_path = find_excel()
    if not excel_path:
        print("Sarcopenia_data.xlsx가 없습니다. 02_info_extract.py를 먼저 실행하세요.")
        sys.exit(1)

    # 기존 결과 로드
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for item in json.load(f):
                existing[item["name"]] = item

    compounds = get_all_compounds(excel_path)
    new_compounds = [c for c in compounds if c not in existing]

    print("=" * 60)
    print(f"  Sarcopenia DCP - 화합물 구조 수집 (PubChem)")
    print(f"  총 화합물: {len(compounds)}개 / 신규: {len(new_compounds)}개")
    print("=" * 60)
    print()

    results = list(existing.values())

    for i, name in enumerate(new_compounds, 1):
        print(f"  [{i}/{len(new_compounds)}] {name}...", end="", flush=True)
        result = query_pubchem(name)
        results.append(result)
        print(f" → {result['status']}")
        time.sleep(0.5)  # API rate limit

    # 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    found = sum(1 for r in results if r["status"] == "found")
    print()
    print(f"  완료! {found}/{len(results)}개 구조 수집")
    print(f"  결과: {OUTPUT_FILE}")

    # Excel로도 저장
    try:
        import pandas as pd
        xlsx_path = os.path.join(BASE_FOLDER, "Sarcopenia_화합물_구조정보.xlsx")
        df = pd.DataFrame([r for r in results if r["status"] == "found"])
        if not df.empty:
            df.to_excel(xlsx_path, index=False, engine="openpyxl")
            print(f"  Excel: {xlsx_path}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
