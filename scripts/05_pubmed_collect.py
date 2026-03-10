"""
=============================================================
05_pubmed_collect.py - PubMed 자동 수집
=============================================================
용도: 근감소증 관련 신규 논문을 PubMed에서 자동 수집
실행: python 05_pubmed_collect.py [--all | --years N]
소요: 30분-1시간
=============================================================
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_FOLDER, "new_papers")
OUTPUT_TXT_DIR = os.path.join(BASE_FOLDER, "new_papers_txt")
COLLECTION_LOG = os.path.join(BASE_FOLDER, "collection_log.json")

# 근감소증 관련 PubMed 검색 쿼리
SEARCH_QUERIES = [
    '(sarcopenia) AND (drug development OR treatment OR therapy OR clinical trial)',
    '(sarcopenia) AND (novel target OR biomarker OR drug discovery)',
    '(muscle wasting OR muscle atrophy) AND (therapeutic OR drug candidate)',
    '(sarcopenia) AND (myostatin OR ActRII OR SARM OR bimagrumab)',
    '(sarcopenia) AND (gut-muscle axis OR microbiome OR probiotic)',
    '(sarcopenia) AND (ferroptosis OR necroptosis OR senescence)',
    '(sarcopenia) AND (exosome OR miRNA OR gene therapy)',
    '(cachexia OR frailty) AND (drug development OR pharmacotherapy)',
    '(sarcopenic obesity) AND (treatment OR intervention)',
    '(muscle regeneration) AND (stem cell OR satellite cell) AND (aging OR elderly)',
]

parser = argparse.ArgumentParser()
parser.add_argument("--all", action="store_true", help="30년 전체 수집")
parser.add_argument("--years", type=int, default=2, help="최근 N년 수집 (기본 2)")
_args, _ = parser.parse_known_args()


def search_pubmed(query, max_results=500, min_date=None, max_date=None):
    """PubMed E-utilities로 검색"""
    import requests

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "date",
    }
    if min_date:
        params["mindate"] = min_date
        params["maxdate"] = max_date or datetime.now().strftime("%Y/%m/%d")
        params["datetype"] = "pdat"

    try:
        resp = requests.get(f"{base_url}/esearch.fcgi", params=params, timeout=30)
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        return ids
    except Exception as e:
        print(f"  검색 실패: {str(e)[:60]}")
        return []


def fetch_details(pmids, batch_size=50):
    """PMID 목록에서 상세 정보 가져오기"""
    import requests

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    results = []

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i+batch_size]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
            "rettype": "abstract",
        }

        try:
            resp = requests.get(f"{base_url}/efetch.fcgi", params=params, timeout=30)
            # 간단한 XML 파싱 (제목, 초록, 연도)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)

            for article in root.findall(".//PubmedArticle"):
                pmid = article.findtext(".//PMID", "")
                title = article.findtext(".//ArticleTitle", "")
                abstract_parts = article.findall(".//AbstractText")
                abstract = " ".join([a.text or "" for a in abstract_parts])
                year = article.findtext(".//PubDate/Year", "")
                if not year:
                    year = article.findtext(".//PubDate/MedlineDate", "")[:4] if article.findtext(".//PubDate/MedlineDate") else ""

                # 저자
                authors = []
                for author in article.findall(".//Author"):
                    last = author.findtext("LastName", "")
                    first = author.findtext("ForeName", "")
                    if last:
                        authors.append(f"{last} {first}".strip())

                # 저널
                journal = article.findtext(".//Journal/Title", "")

                results.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "year": year,
                    "authors": authors[:5],
                    "journal": journal,
                    "source": "pubmed",
                    "collected_at": datetime.now().isoformat(),
                })

        except Exception as e:
            print(f"  상세정보 실패 (batch {i}): {str(e)[:60]}")

        time.sleep(0.5)

    return results


def main():
    try:
        import requests
    except ImportError:
        print("pip install requests")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_TXT_DIR, exist_ok=True)

    # 기존 수집 로그
    existing_pmids = set()
    collection_log = []
    if os.path.exists(COLLECTION_LOG):
        with open(COLLECTION_LOG, "r", encoding="utf-8") as f:
            collection_log = json.load(f)
        existing_pmids = {str(e.get("pmid", "")) for e in collection_log if "pmid" in e}

    # 날짜 범위
    if _args.all:
        min_date = "1995/01/01"
        print("  모드: 전체 (1995~)")
    else:
        min_date = (datetime.now() - timedelta(days=365 * _args.years)).strftime("%Y/%m/%d")
        print(f"  모드: 최근 {_args.years}년")

    max_date = datetime.now().strftime("%Y/%m/%d")

    print("=" * 60)
    print(f"  Sarcopenia DCP - PubMed 자동 수집")
    print(f"  기간: {min_date} ~ {max_date}")
    print(f"  기존 수집: {len(existing_pmids)}건")
    print("=" * 60)
    print()

    all_new = []

    for qi, query in enumerate(SEARCH_QUERIES, 1):
        print(f"  [{qi}/{len(SEARCH_QUERIES)}] 검색: {query[:60]}...")
        pmids = search_pubmed(query, max_results=500, min_date=min_date, max_date=max_date)
        new_pmids = [p for p in pmids if p not in existing_pmids]
        print(f"    결과: {len(pmids)}건 / 신규: {len(new_pmids)}건")

        if new_pmids:
            details = fetch_details(new_pmids)
            all_new.extend(details)
            for d in details:
                existing_pmids.add(str(d["pmid"]))

        time.sleep(1)

    # 중복 제거
    seen = set()
    unique_new = []
    for item in all_new:
        if item["pmid"] not in seen:
            seen.add(item["pmid"])
            unique_new.append(item)

    print(f"\n  총 신규 논문: {len(unique_new)}건")

    # 텍스트 파일로 저장 (초록)
    saved = 0
    for item in unique_new:
        title = item.get("title", "")
        abstract = item.get("abstract", "")
        if abstract and len(abstract) > 100:
            safe_title = "".join(c for c in title[:80] if c.isalnum() or c in " -_").strip()
            txt_filename = f"{safe_title}.txt"
            txt_path = os.path.join(OUTPUT_TXT_DIR, txt_filename)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\n\n")
                f.write(f"Authors: {', '.join(item.get('authors', []))}\n")
                f.write(f"Journal: {item.get('journal', '')}\n")
                f.write(f"Year: {item.get('year', '')}\n")
                f.write(f"PMID: {item.get('pmid', '')}\n\n")
                f.write(f"Abstract:\n{abstract}\n")
            item["txt_file"] = txt_filename
            saved += 1

    # 수집 로그 업데이트
    collection_log.extend(unique_new)
    with open(COLLECTION_LOG, "w", encoding="utf-8") as f:
        json.dump(collection_log, f, ensure_ascii=False, indent=2)

    print(f"  텍스트 저장: {saved}건")
    print(f"  수집 로그: {COLLECTION_LOG} (총 {len(collection_log)}건)")
    print(f"\n  다음: python 06_patent_collect.py")


if __name__ == "__main__":
    main()
