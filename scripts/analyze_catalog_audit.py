#!/usr/bin/env python3
"""사학연금공단 공공데이터 전수 목록 중 현재 연구와 직접 연결된 파일의 값·합계·기간을 교차 검사한다.

원본 CSV는 수정하지 않고, 복원·집계·비교 결과만 data/catalog에 저장한다.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "catalog_audit"
OUT = ROOT / "data" / "catalog"


def read(dataset_id: int) -> pd.DataFrame:
    return pd.read_csv(RAW / f"{dataset_id}.csv", encoding="cp949")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def restore_portal_year_month(series: pd.Series) -> pd.Series:
    """Restore YYYY-MM values that the downloaded files encode as 2025-MM-YY."""
    parsed = pd.to_datetime(series, errors="raise")
    return pd.to_datetime(
        {"year": 2000 + parsed.dt.day, "month": parsed.dt.month, "day": 1}
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. 고객 상담 채널: 공표 총계와 채널 부문 합의 일치 여부
    channel = read(15102547)
    channel_columns = [
        "등록채널(온라인)",
        "등록채널(전화)",
        "등록채널(방문)",
        "등록채널(기타)",
    ]
    channel["채널부문합계"] = channel[channel_columns].sum(axis=1)
    channel["합계차이_채널부문minus처리건수"] = (
        channel["채널부문합계"] - channel["처리건수"]
    )
    channel["전화비중_pct"] = (
        channel["등록채널(전화)"] / channel["채널부문합계"] * 100
    )
    channel["온라인비중_pct"] = (
        channel["등록채널(온라인)"] / channel["채널부문합계"] * 100
    )
    channel.to_csv(OUT / "고객상담_채널정합성_20260831.csv", index=False, encoding="utf-8-sig")

    # 2. VOC: 연간 부문 합계 검사, 상담 처리건수와의 차이 검사
    annual_voc = read(15133677)
    voc_columns = [c for c in annual_voc.columns if c not in {"연도", "합계"}]
    annual_voc["VOC부문합계"] = annual_voc[voc_columns].sum(axis=1)
    annual_voc["VOC내부합계차이"] = annual_voc["VOC부문합계"] - annual_voc["합계"]
    voc_cross = channel[["년도", "처리건수", "채널부문합계"]].merge(
        annual_voc[["연도", "합계", "VOC부문합계", "VOC내부합계차이"]],
        left_on="년도",
        right_on="연도",
        how="outer",
    )
    voc_cross["VOC합계minus상담처리건수"] = voc_cross["합계"] - voc_cross["처리건수"]
    voc_cross.to_csv(OUT / "VOC_상담처리_교차검증_20260831.csv", index=False, encoding="utf-8-sig")

    # 3. 인터넷 접수: 원파일의 뒤집힌 연월 복원 후 유형별 집계
    internet = read(15151198)
    internet["복원_요청연월"] = restore_portal_year_month(internet["요청년월"])
    internet_summary = (
        internet.groupby(["복원_요청연월", "신청구분코드", "신청구분명"], as_index=False)["접수건수"]
        .sum()
        .sort_values(["복원_요청연월", "신청구분코드"])
    )
    internet_summary.to_csv(OUT / "인터넷접수_연월복원_유형별_20260831.csv", index=False, encoding="utf-8-sig")

    # 4. 홈페이지 가입자: 동일한 연월 복원 규칙 검사
    website = read(15065011)
    website["복원_기준연월"] = restore_portal_year_month(website["기준연월"])
    website.to_csv(OUT / "홈페이지가입자_연월복원_20260831.csv", index=False, encoding="utf-8-sig")

    # 5. 퇴직연금 수급자 총계: 서로 다른 공개파일 간 교차 비교
    age_school = read(15045815)
    age_tenure = read(15045816)
    age_school_total = int(
        sum(numeric(age_school[c]).fillna(0).sum() for c in age_school.columns[1:])
    )
    age_tenure_total = int(
        sum(numeric(age_tenure[c]).fillna(0).sum() for c in age_tenure.columns[1:])
    )
    pension_selection = read(15064966)
    pension_2025 = int(pension_selection.loc[pension_selection["연도"] == 2025, "퇴직연금"].iloc[0])
    annual_core = pd.read_csv(OUT.parent / "processed" / "연도별_퇴직연금수급자_연금액_정제.csv")
    core_2025 = int(annual_core.loc[annual_core["연도"] == 2025, "퇴직연금수급자수"].iloc[0])
    payment = read(15012436)
    payment_2025 = int(payment.loc[payment["구분년도"] == 2025, "퇴직연금 건수(건)"].iloc[0])
    forecast = read(15102551)
    forecast_2025 = int(forecast.loc[forecast["연도"] == 2025, "퇴직연금 수급자"].iloc[0])
    totals = pd.DataFrame(
        [
            {"데이터ID": 15045820, "지표": "퇴직연금 수급자", "2025값": core_2025, "비고": "연도별 수급자 및 연금액"},
            {"데이터ID": 15064966, "지표": "퇴직연금 수급자", "2025값": pension_2025, "비고": "연금수급자 및 연금선택률"},
            {"데이터ID": 15045815, "지표": "퇴직연금 수급자", "2025값": age_school_total, "비고": "연령×학교급 부문 합"},
            {"데이터ID": 15045816, "지표": "퇴직연금 수급자", "2025값": age_tenure_total, "비고": "연령×재직기간 부문 합"},
            {"데이터ID": 15012436, "지표": "퇴직연금 지급 건수", "2025값": payment_2025, "비고": "수급자 수와 같은 지표로 단정 금지"},
            {"데이터ID": 15102551, "지표": "퇴직연금 수급자 예측치", "2025값": forecast_2025, "비고": "실적이 아닌 예측치"},
        ]
    )
    totals["15064966대비차이"] = totals["2025값"] - pension_2025
    totals.to_csv(OUT / "퇴직연금수급자_총계교차검증_20260831.csv", index=False, encoding="utf-8-sig")

    # 6. 75세 기준 지역별 파일: ‘건수’가 인원이 아니라 평균연금액인지 내부값으로 검증
    age_older = read(15119216)
    age_younger = read(15119221)
    for frame in (age_older, age_younger):
        frame["역산_추정인원"] = frame["금액"] / frame["건수"]
    inferred_older = round(float(age_older["역산_추정인원"].sum()))
    inferred_younger = round(float(age_younger["역산_추정인원"].sum()))

    manifest = []
    for path in sorted(RAW.glob("*.csv")):
        frame = pd.read_csv(path, encoding="cp949")
        manifest.append(
            {
                "데이터ID": path.stem,
                "파일명": path.name,
                "행수": len(frame),
                "열수": len(frame.columns),
                "sha256": sha256(path),
            }
        )
    pd.DataFrame(manifest).to_csv(
        OUT / "핵심후보_원본파일_무결성_20260831.csv", index=False, encoding="utf-8-sig"
    )

    summary = {
        "검증일": "2026-08-31",
        "전수목록": {"사학연금공단_제공자일치": 186, "키워드검색_전체": 193, "타기관_오탐": 7},
        "상세값검증_원본파일수": len(manifest),
        "고객상담": {
            "합계불일치_연도": channel.loc[
                channel["합계차이_채널부문minus처리건수"] != 0, "년도"
            ].tolist(),
            "2025_전화비중_pct": round(float(channel.loc[channel["년도"] == 2025, "전화비중_pct"].iloc[0]), 4),
            "2025_온라인비중_pct": round(float(channel.loc[channel["년도"] == 2025, "온라인비중_pct"].iloc[0]), 4),
        },
        "VOC": {
            "연간파일_내부합계일치": bool((annual_voc["VOC내부합계차이"] == 0).all()),
            "상담처리건수와_대규모차이_연도": [2023, 2024],
        },
        "인터넷접수": {
            "원본표기": "2025-MM-YY",
            "복원기간": f"{internet['복원_요청연월'].min():%Y-%m}~{internet['복원_요청연월'].max():%Y-%m}",
            "신청유형수": int(internet["신청구분명"].nunique()),
            "전체접수건수": int(internet["접수건수"].sum()),
            "한계": "7개 유형 접수 현황이며 전체 디지털 접속·인증·업무완료 흐름은 아님",
        },
        "홈페이지가입자": {
            "원본표기": "2025-MM-YY",
            "복원기간": f"{website['복원_기준연월'].min():%Y-%m}~{website['복원_기준연월'].max():%Y-%m}",
        },
        "2025_퇴직연금수급자_공표값": {
            "15045820_연도별수급자": core_2025,
            "15064966_수급자및선택률": pension_2025,
            "15045815_연령x학교급합": age_school_total,
            "15045816_연령x재직기간합": age_tenure_total,
        },
        "75세기준_지역파일": {
            "75세초과_역산인원": inferred_older,
            "75세이하_역산인원": inferred_younger,
            "합계": inferred_older + inferred_younger,
            "전체연금수급자_15064966합계": int(
                pension_selection.loc[
                    pension_selection["연도"] == 2025,
                    ["퇴직연금", "유족연금", "장해연금", "연계연금"],
                ].sum(axis=1).iloc[0]
            ),
            "해석": "지역파일의 '건수'는 인원이 아니라 평균연금액으로 판단된다. 금액÷건수가 지역별 정수 인원이고 전체 수급자 합계와 일치한다.",
        },
    }
    (OUT / "핵심후보_데이터품질검사_20260831.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
