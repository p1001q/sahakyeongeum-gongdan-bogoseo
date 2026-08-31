#!/usr/bin/env python3
"""공공데이터포털 검색결과에서 사학연금공단 데이터 목록을 추출·분류한다."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from lxml import html


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "catalog"
PROVIDER = "사립학교교직원연금공단"


def clean(text: str) -> str:
    return " ".join(text.split())


def primary_category(title: str) -> str:
    rules = [
        ("고객·디지털·VOC", r"VOC|고객|상담|홈페이지|인터넷 접수|유튜브|SNS|콜센터|민원"),
        ("퇴직·급여", r"퇴직|급여종류별지급|수급종료"),
        ("연금수급자", r"수급자|연금월액|연금수령|분할연금"),
        ("가입·재직·기관", r"가입|재직|학교기관|연금법 적용|기준소득|부담률|부담금"),
        ("대여·복지·재해보상", r"대여|복지|재해|요양|학자금|사망조위|법률자문"),
        ("기금·투자·재무", r"기금|투자|위탁운용|VaR|수익률|자산운용|재무|예산집행"),
        ("기관운영·ESG", r"채용|구매|감사|차량|온실가스|에너지|기부|사회공헌|회관|소화기"),
        ("법령·콘텐츠·기타", r"."),
    ]
    for category, pattern in rules:
        if re.search(pattern, title, re.I):
            return category
    raise AssertionError(title)


def relevance(title: str, summary: str, keywords: str) -> str:
    text = " ".join((title, summary, keywords))
    if re.search(
        r"퇴직|수급자|연금월액|수급종료|급여종류별지급|인터넷 접수|상담 채널|VOC|홈페이지|공공데이터 목록|가입자 수 예측",
        text,
        re.I,
    ):
        return "검토대상"
    if re.search(r"가입|재직|기준소득|급여|연금|상담|민원|서비스", text, re.I):
        return "보조검토"
    return "현재주제 제외"


def extract(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page, path in enumerate(paths, start=1):
        doc = html.parse(str(path))
        items = doc.xpath(
            '//div[contains(concat(" ",normalize-space(@class)," ")," apply-result-item ")]'
        )
        for rank_in_page, item in enumerate(items, start=1):
            links = item.xpath('.//div[contains(@class,"apply-result-link")]/a')
            if not links:
                continue
            link = links[0]
            title = clean(link.text_content())
            url = "https://www.data.go.kr" + link.get("href")
            summaries = item.xpath('.//span[contains(@class,"apply-result-summary")]')
            summary = clean(summaries[0].text_content()) if summaries else ""
            meta: dict[str, str] = {}
            for li in item.xpath(".//ul/li"):
                strong = li.xpath("./strong")
                if not strong:
                    continue
                key = clean(strong[0].text_content())
                full = clean(li.text_content())
                meta[key] = full[len(key) :].strip()
            provider = meta.get("제공기관", "")
            if provider != PROVIDER:
                continue
            dataset_id_match = re.search(r"/data/(\d+)/", url)
            dataset_id = dataset_id_match.group(1) if dataset_id_match else ""
            category = primary_category(title)
            keywords = meta.get("키워드", "")
            rows.append(
                {
                    "검색순위": str((page - 1) * 40 + rank_in_page),
                    "데이터ID": dataset_id,
                    "데이터명": title,
                    "설명": summary,
                    "키워드": keywords,
                    "수정일": meta.get("수정일", ""),
                    "조회수": meta.get("조회수", ""),
                    "다운로드": meta.get("다운로드", ""),
                    "대분류": category,
                    "현재연구관련성": relevance(title, summary, keywords),
                    "공식URL": url,
                }
            )
    return rows


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        raise SystemExit("검색결과 HTML 경로를 인수로 지정하세요.")
    rows = extract(paths)
    if len(rows) != 186:
        raise ValueError(f"사학연금공단 데이터가 186건이어야 하나 {len(rows)}건 추출됨")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "사학연금공단_공공데이터_186개_목록_20260831.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "확인일": "2026-08-31",
        "공식검색결과전체": 193,
        "사학연금공단제공": len(rows),
        "검색어오탐": 7,
        "대분류건수": dict(Counter(r["대분류"] for r in rows)),
        "관련성건수": dict(Counter(r["현재연구관련성"] for r in rows)),
        "검색URL": "https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=사립학교교직원연금공단",
        "주의": "현재 단계는 목록 메타데이터 전수분류다. 연구 관련 후보는 상세 페이지의 컬럼·기간·기준을 추가 검증해야 한다.",
    }
    json_path = OUT_DIR / "사학연금공단_공공데이터_186개_분류요약_20260831.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
