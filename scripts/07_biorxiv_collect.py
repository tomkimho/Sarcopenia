"""
=============================================================
07_biorxiv_collect.py - bioRxiv/medRxiv 프리프린트 수집
=============================================================
용도: 근감소증 관련 프리프린트 자동 수집
실행: python 07_biorxiv_collect.py
소요: ~5분
=============================================================
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_TXT_DIR = os.path.join(BASE_FOLDER, "new_papers_txt")
COLLECTION_LOG = os.path.join(BASE_FOLDER, "collection_log.json")


def search_biorxiv(query, server="biorxiv", days_back=90):
    """bioRxiv/medRxiv API로 검색"""
    import requests

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    results = []
    cursor = 0

    while True:
        url = f"https://api.biorxiv.org/details/{server}/{start_date}/{end_date}/{cursor}"
        try:
            resp = requests.get(url, timeout=30)
            data = resp.json()
            collection = data.get("collection", [])

            if not collection:
                break

            for item in collection:
                title = item.get("title", "").lower()
                abstract = item.get("abstract", "").lower()
                text = title + " " + abstract

                # 키워드 매칭
                keywords = ["sarcopenia", "muscle wasting", "muscle atrophy",
                           "cachexia", "frailty", "myostatin", "muscle mass",
                           "skeletal muscle aging", "muscle regeneration"]

                if any(kw in text for kw in keywords):
                    results.append({
                        "doi": item.get("doi", ""),
                        "title": item.get("title", ""),
                        "authors": item.get("authors", ""),
                        "abstract": item.get("abstract", ""),
                        "date": item.get("date", ""),
                        "category": item.get("category", ""),
                        "source": server,
                        "collected_at": datetime.now().isoformat(),
                    })

            cursor += len(collection)
            if cursor >= int(data.get("messages", [{}])[0].get("total", 0)):
                break

            time.sleep(0.5)

        except Exception as e:
            print(f"  API 오류: {str(e)[:60]}")
            break

    return results


def main():
    try:
        import requests
    except ImportError:
        print("pip install requests")
        sys.exit(1)

    os.makedirs(OUTPUT_TXT_DIR, exist_ok=True)

    # 기존 로그
    collection_log = []
    existing_dois = set()
    if os.path.exists(COLLECTION_LOG):
        with open(COLLECTION_LOG, "r", encoding="utf-8") as f:
            collection_log = json.load(f)
        existing_dois = {str(e.get("doi", "")) for e in collection_log if "doi" in e}

    print("=" * 60)
    print(f"  Sarcopenia DCP - bioRxiv/medRxiv 프리프린트 수집")
    print(f"  기존 프리프린트: {len(existing_dois)}건")
    print("=" * 60)
    print()

    all_new = []

    for server in ["biorxiv", "medrxiv"]:
        print(f"  {server} 검색 중...")
        results = search_biorxiv("sarcopenia", server=server, days_back=90)
        new_results = [r for r in results if r.get("doi", "") not in existing_dois]
        print(f"    결과: {len(results)}건 / 신규: {len(new_results)}건")
        all_new.extend(new_results)
        for r in new_results:
            existing_dois.add(r.get("doi", ""))

    # 텍스트 저장
    saved = 0
    for item in all_new:
        title = item.get("title", "")
        abstract = item.get("abstract", "")
        if abstract and len(abstract) > 100:
            safe_title = "".join(c for c in title[:80] if c.isalnum() or c in " -_").strip()
            txt_filename = f"{safe_title}.txt"
            txt_path = os.path.join(OUTPUT_TXT_DIR, txt_filename)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\n\n")
                f.write(f"Authors: {item.get('authors', '')}\n")
                f.write(f"Date: {item.get('date', '')}\n")
                f.write(f"DOI: {item.get('doi', '')}\n")
                f.write(f"Source: {item.get('source', '')}\n\n")
                f.write(f"Abstract:\n{abstract}\n")
            item["txt_file"] = txt_filename
            saved += 1

    # 로그 업데이트
    collection_log.extend(all_new)
    with open(COLLECTION_LOG, "w", encoding="utf-8") as f:
        json.dump(collection_log, f, ensure_ascii=False, indent=2)

    print(f"\n  신규 프리프린트: {len(all_new)}건 / 텍스트 저장: {saved}건")
    print(f"  수집 로그: {COLLECTION_LOG} (총 {len(collection_log)}건)")
    print(f"\n  다음: python 08_orchestrator.py")


if __name__ == "__main__":
    main()
