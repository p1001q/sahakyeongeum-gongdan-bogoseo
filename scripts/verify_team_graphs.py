#!/usr/bin/env python3
"""팀원 제공 그래프 7종의 핵심 수치를 공식 원자료와 재검산한다."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEAM_RAW = ROOT / "data" / "raw" / "team_contributed"
OUTPUT = ROOT / "output" / "evidence" / "팀원_그래프_재검산_20260831.json"

TP_STATUS_URL = "https://www.tp.or.kr/tp-kr/pgm/i-168/newsinfo/stats/suber/front/list.do"
RETIRE_REASON_URL = "https://www.data.go.kr/data/15131720/fileData.do"
PENSION_AMOUNT_URL = "https://www.data.go.kr/data/15045812/fileData.do"


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def find_csv(keyword: str) -> Path:
    matches = [p for p in TEAM_RAW.glob("*.csv") if keyword in nfc(p.name)]
    if len(matches) != 1:
        raise RuntimeError(f"{keyword!r} CSV를 하나로 특정하지 못함: {matches}")
    return matches[0]


def read_cp949(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="cp949", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value: str | None) -> int:
    if value is None or value.strip() == "":
        return 0
    return int(float(value))


def age_label_number(label: str) -> int:
    found = re.search(r"\d+", label)
    if not found:
        raise ValueError(label)
    return int(found.group())


def team_age_band(label: str) -> str:
    """팀원 그래프가 사용한 구간: 표기 숫자 자체를 연령으로 취급."""
    age = age_label_number(label)
    if age < 60:
        return "60세 미만"
    if age < 70:
        return "60대"
    if age < 80:
        return "70대"
    if age < 90:
        return "80대"
    return "90세 이상"


def semantic_age_band(label: str) -> str:
    """'60미만'을 60세 미만에 포함하는 문언 기준 구간."""
    if "이상" in label:
        return "90세 이상"
    upper = age_label_number(label)
    representative_age = upper - 1
    if representative_age < 60:
        return "60세 미만"
    if representative_age < 70:
        return "60대"
    if representative_age < 80:
        return "70대"
    if representative_age < 90:
        return "80대"
    return "90세 이상"


def weighted_average(rows: list[dict[str, str]]) -> float:
    numerator = 0
    denominator = 0
    for row in rows:
        for count_col, amount_col in (
            ("교원 남성수급자수(명)", "교원 남성 1인당 평균연금월액(원)"),
            ("교원 여성 수급자수(명)", "교원 여성 1인당 평균연금월액(원)"),
        ):
            count = number(row[count_col])
            numerator += count * number(row[amount_col])
            denominator += count
    return numerator / denominator


def age_results() -> dict:
    rows = read_cp949(find_csv("평균연금월액"))
    count_columns = [
        "교원 남성수급자수(명)",
        "교원 여성 수급자수(명)",
        "사무직원 남성수급자수(명)",
        "사무직원 여성 수급자수(명)",
    ]
    total = sum(number(row[col]) for row in rows for col in count_columns)

    result: dict[str, object] = {"총수급자수": total, "구간비교": {}}
    for method_name, band_func in (
        ("팀원_표기숫자기준", team_age_band),
        ("미만_문언기준", semantic_age_band),
    ):
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[band_func(row["연령"])].append(row)

        band_result = {}
        for band, band_rows in grouped.items():
            teacher = sum(
                number(row["교원 남성수급자수(명)"])
                + number(row["교원 여성 수급자수(명)"])
                for row in band_rows
            )
            staff = sum(
                number(row["사무직원 남성수급자수(명)"])
                + number(row["사무직원 여성 수급자수(명)"])
                for row in band_rows
            )
            band_result[band] = {
                "교원": teacher,
                "사무직원": staff,
                "합계": teacher + staff,
                "교원_가중평균월액_원": round(weighted_average(band_rows)),
            }
        result["구간비교"][method_name] = band_result

    amount_columns = [key for key in rows[0] if "평균연금월액" in key]
    result["원자료_월액범위_원"] = {
        col: {
            "최소": min(number(row[col]) for row in rows),
            "최대": max(number(row[col]) for row in rows),
        }
        for col in amount_columns
    }
    return result


def retirement_reason_results() -> dict:
    rows = read_cp949(find_csv("퇴직사유별 퇴직자 현황"))
    value_columns = [key for key in rows[0] if key not in {"기준년도", "지역", "퇴직사유"}]
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        totals[row["퇴직사유"]] += sum(number(row[col]) for col in value_columns)

    annual_path = ROOT / "data" / "raw" / "사립학교교직원연금공단_연도별_교직원_퇴직현황_20251231.csv"
    annual_rows = read_cp949(annual_path)
    annual_2025 = next(number(row["교원"]) for row in annual_rows if row["연도"] == "2025")
    reason_total = sum(totals.values())
    return {
        "퇴직사유별_합계": dict(sorted(totals.items(), key=lambda item: item[1], reverse=True)),
        "퇴직사유파일_총계": reason_total,
        "연도별퇴직현황파일_교원총계": annual_2025,
        "공식파일간_차이": annual_2025 - reason_total,
    }


def pension_status_results() -> dict:
    # 2026-08-31 사학연금 홈페이지 '연도별 가입 현황' 확인값.
    subscribers = {2021: 330_322, 2022: 333_231, 2023: 333_852, 2024: 323_542, 2025: 332_359}
    recipients = {2021: 98_730, 2022: 106_896, 2023: 115_224, 2024: 123_274, 2025: 130_913}
    net = {year: recipients[year] - recipients[year - 1] for year in range(2022, 2026)}
    ratio = {year: round(recipients[year] / subscribers[year] * 100, 1) for year in range(2021, 2025)}
    shown_net = {2022: 8_163, 2023: 8_324, 2024: 8_045, 2025: 7_635}
    shown_ratio = {2021: 30.1, 2022: 32.4, 2023: 34.5, 2024: 38.0}
    return {
        "가입자": subscribers,
        "전체연금수급자": recipients,
        "공식값_순증": net,
        "그래프표기_순증": shown_net,
        "순증_그래프표기차이": {year: shown_net[year] - net[year] for year in net},
        "정확값_가입자대비수급자비율_pct": ratio,
        "그래프표기_비율_pct": shown_ratio,
        "비율_그래프표기차이_pp": {year: round(shown_ratio[year] - ratio[year], 1) for year in ratio},
    }


def main() -> None:
    payload = {
        "검증일": "2026-08-31",
        "출처": {
            "사학연금_가입자현황": TP_STATUS_URL,
            "퇴직사유": RETIRE_REASON_URL,
            "평균연금월액": PENSION_AMOUNT_URL,
        },
        "수급자순증_가입자대비비율": pension_status_results(),
        "퇴직사유": retirement_reason_results(),
        "연령_평균연금월액": age_results(),
    }

    assert payload["수급자순증_가입자대비비율"]["공식값_순증"] == {
        2022: 8_166,
        2023: 8_328,
        2024: 8_050,
        2025: 7_639,
    }
    assert payload["퇴직사유"]["퇴직사유파일_총계"] == 14_193
    assert payload["퇴직사유"]["공식파일간_차이"] == 596
    assert payload["연령_평균연금월액"]["총수급자수"] == 118_656

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
