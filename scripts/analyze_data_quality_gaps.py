#!/usr/bin/env python3
"""Ⅴ장 분석 공백·공공데이터 품질진단의 사례표와 검증 그림을 재현한다."""

from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
AUDIT = RAW / "catalog_audit"
PROCESSED = ROOT / "data" / "processed"
CATALOG = ROOT / "data" / "catalog"
EVIDENCE = ROOT / "output" / "evidence"
FIGURES = ROOT / "output" / "figures" / "verified"

TASK_CACHE = Path(tempfile.gettempdir()) / "tp-quality-gap-cache"
TASK_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TASK_CACHE / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TASK_CACHE / "xdg"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter


NAVY = "#24364B"
BLUE = "#138ACB"
MID_BLUE = "#4C78A8"
PURPLE = "#7A6FA6"
CORAL = "#D66A5E"
GRAY = "#68737D"
LIGHT_GRAY = "#E7E4ED"
INK = "#222222"


def read(dataset_id: int) -> pd.DataFrame:
    return pd.read_csv(AUDIT / f"{dataset_id}.csv", encoding="cp949")


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def find_team_csv(keyword: str) -> Path:
    matches = [path for path in (RAW / "team_contributed").glob("*.csv") if keyword in nfc(path.name)]
    if len(matches) != 1:
        raise RuntimeError(f"{keyword!r} 파일을 하나로 특정하지 못함: {matches}")
    return matches[0]


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def configure_plotting() -> None:
    korean_font = Path(
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
        "7a0b5c0f3c1d41c4c52a33343496c9c65ad52c50.asset/AssetData/NanumGothic.ttc"
    )
    if not korean_font.exists():
        korean_font = Path("/System/Library/Fonts/AppleSDGothicNeo.ttc")
    font_manager.fontManager.addfont(str(korean_font))
    family = font_manager.FontProperties(fname=str(korean_font)).get_name()
    mpl.rcParams.update(
        {
            "font.family": family,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#BCC5CC",
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": GRAY,
            "ytick.color": GRAY,
            "axes.titleweight": "bold",
            "axes.titlesize": 16,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
            "figure.dpi": 150,
            "savefig.dpi": 240,
        }
    )


def style_axis(ax: plt.Axes, grid_axis: str = "x") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid_axis, color="#DDE3E8", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)


def add_source(fig: plt.Figure, source: str, note: str) -> None:
    fig.text(0.01, 0.01, f"출처: {source}  |  주: {note}", ha="left", va="bottom", fontsize=7.1, color=GRAY)


def save(fig: plt.Figure, filename: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / filename, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def pension_totals() -> tuple[pd.DataFrame, dict]:
    annual = pd.read_csv(PROCESSED / "연도별_퇴직연금수급자_연금액_정제.csv")
    value_15045820 = int(annual.loc[annual["연도"] == 2025, "퇴직연금수급자수"].iloc[0])

    selection = read(15064966)
    value_15064966 = int(selection.loc[selection["연도"] == 2025, "퇴직연금"].iloc[0])

    age_school = read(15045815)
    value_15045815 = int(sum(numeric(age_school[c]).fillna(0).sum() for c in age_school.columns[1:]))

    age_tenure = read(15045816)
    value_15045816 = int(sum(numeric(age_tenure[c]).fillna(0).sum() for c in age_tenure.columns[1:]))

    frame = pd.DataFrame(
        [
            {"데이터ID": 15045820, "자료구분": "연도별 수급자·연금액", "2025값": value_15045820},
            {"데이터ID": 15064966, "자료구분": "연금수급자·선택률", "2025값": value_15064966},
            {"데이터ID": 15045815, "자료구분": "연령×학교급 부문합", "2025값": value_15045815},
            {"데이터ID": 15045816, "자료구분": "재직기간×연령 부문합", "2025값": value_15045816},
        ]
    )
    frame["15045820대비차이"] = frame["2025값"] - value_15045820
    assert frame["2025값"].tolist() == [111_389, 114_079, 114_079, 118_656]
    metrics = {
        "공표값": {str(row["데이터ID"]): int(row["2025값"]) for _, row in frame.iterrows()},
        "114079_minus_111389": value_15064966 - value_15045820,
        "118656_minus_114079": value_15045816 - value_15064966,
        "118656_minus_111389": value_15045816 - value_15045820,
        "판정": "자료별 기준일·모집단·집계 정의가 충분히 설명되지 않아 하나의 총계로 통합하지 않음",
    }
    return frame, metrics


def channel_differences() -> tuple[pd.DataFrame, dict]:
    channel = read(15102547)
    parts = ["등록채널(온라인)", "등록채널(전화)", "등록채널(방문)", "등록채널(기타)"]
    channel["채널부문합계"] = channel[parts].sum(axis=1)
    channel["차이_채널합minus처리건수"] = channel["채널부문합계"] - channel["처리건수"]
    channel["불일치율_pct"] = channel["차이_채널합minus처리건수"].abs() / channel["처리건수"] * 100
    recent = channel[channel["년도"].between(2023, 2025)][
        ["년도", "처리건수", "채널부문합계", "차이_채널합minus처리건수", "불일치율_pct"]
    ].copy()
    assert recent["차이_채널합minus처리건수"].tolist() == [-526, 8967, -44]
    metrics = {
        str(int(row["년도"])): {
            "처리건수": int(row["처리건수"]),
            "채널부문합계": int(row["채널부문합계"]),
            "차이": int(row["차이_채널합minus처리건수"]),
            "절대불일치율_pct": round(float(row["불일치율_pct"]), 4),
        }
        for _, row in recent.iterrows()
    }
    return recent, metrics


def date_quality() -> dict:
    internet = read(15151198)
    website = read(15065011)
    parsed_i = pd.to_datetime(internet["요청년월"], errors="raise")
    parsed_w = pd.to_datetime(website["기준연월"], errors="raise")
    restored_i = pd.to_datetime({"year": 2000 + parsed_i.dt.day, "month": parsed_i.dt.month, "day": 1})
    restored_w = pd.to_datetime({"year": 2000 + parsed_w.dt.day, "month": parsed_w.dt.month, "day": 1})
    return {
        "인터넷접수_15151198": {
            "행수": int(len(internet)),
            "원본예시": internet["요청년월"].iloc[0],
            "복원기간": f"{restored_i.min():%Y-%m}~{restored_i.max():%Y-%m}",
        },
        "홈페이지가입자_15065011": {
            "행수": int(len(website)),
            "원본예시": website["기준연월"].iloc[0],
            "복원기간": f"{restored_w.min():%Y-%m}~{restored_w.max():%Y-%m}",
        },
        "복원규칙": "연도=2000+원본 day, 월=원본 month; 원본은 덮어쓰지 않음",
    }


def regional_columns() -> dict:
    older = read(15119216)
    younger = read(15119221)
    older_inferred = (older["금액"] / older["건수"]).round().astype(int)
    younger_inferred = (younger["금액"] / younger["건수"]).round().astype(int)
    older_total = int(older_inferred.sum())
    younger_total = int(younger_inferred.sum())
    assert (older_total, younger_total, older_total + younger_total) == (29_584, 101_329, 130_913)
    return {
        "공표컬럼": ["지역", "건수", "금액"],
        "건수열_범위": {
            "75세초과": [int(older["건수"].min()), int(older["건수"].max())],
            "75세이하": [int(younger["건수"].min()), int(younger["건수"].max())],
        },
        "역산규칙": "지역별 금액÷건수 후 반올림하고 합산",
        "역산인원": {"75세초과": older_total, "75세이하": younger_total, "합계": older_total + younger_total},
        "교차값": "ID 15064966의 2025년 전체 연금수급자 130,913명과 일치",
        "판정": "건수열이 평균연금액일 가능성이 강하지만 공식 컬럼 정의 확인 전 확정하지 않음",
    }


def supplementary_cases() -> dict:
    retire = pd.read_csv(RAW / "사립학교교직원연금공단_연도별_교직원_퇴직현황_20251231.csv", encoding="cp949")
    annual_teacher = int(retire.loc[retire["연도"] == 2025, "교원"].iloc[0])
    reason = pd.read_csv(find_team_csv("퇴직사유별 퇴직자 현황"), encoding="cp949")
    value_columns = [c for c in reason.columns if c not in {"기준년도", "지역", "퇴직사유"}]
    reason_total = int(reason[value_columns].sum().sum())
    assert (annual_teacher, reason_total, annual_teacher - reason_total) == (14_789, 14_193, 596)

    average = pd.read_csv(find_team_csv("평균연금월액"), encoding="cp949")
    amount_columns = [c for c in average.columns if "평균연금월액" in c]
    maximum = int(average[amount_columns].max().max())
    assert maximum == 49_820_709
    return {
        "교원퇴직자": {
            "연도별파일": annual_teacher,
            "퇴직사유파일내부합": reason_total,
            "차이": annual_teacher - reason_total,
            "판정": "기준일·학교급 포함범위·집계 정의 확인 전 오류 단정 금지",
        },
        "평균연금월액_15045812": {
            "메타데이터단위": "원",
            "원값최대": maximum,
            "판정": "단위·값 생성방식 확인 전 실제 연금수준 분석 금지",
        },
    }


def build_quality_cases(metrics: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"사례ID": "Q1", "유형": "정합성", "우선순위": "1", "확인된사례": "2025년 퇴직연금수급자 111,389·114,079·118,656명", "분석영향": "자료 간 총계 교차사용 불가", "개선조치": "기준일·모집단·포함범위·산식·정정이력 명시", "품질KPI": "핵심지표 정의완결률"},
            {"사례ID": "Q2", "유형": "정합성", "우선순위": "1", "확인된사례": "상담 채널 합-처리건수: 2023 -526, 2024 +8,967, 2025 -44건", "분석영향": "채널 비중 분모가 달라짐", "개선조치": "총계 자동검증·미분류/중복 기준 공개", "품질KPI": "부문합계 일치율"},
            {"사례ID": "Q3", "유형": "구조", "우선순위": "1", "확인된사례": "인터넷 접수·홈페이지 가입자의 2025-MM-YY 연월 표기", "분석영향": "2025년 일별자료로 오독 가능", "개선조치": "YYYY-MM 표준·날짜형 검증", "품질KPI": "표준연월 준수율"},
            {"사례ID": "Q4", "유형": "정의", "우선순위": "1", "확인된사례": "75세 지역파일의 건수열 값이 550,539~3,319,250", "분석영향": "수급자 인원으로 직접 그래프화하면 왜곡", "개선조치": "컬럼명·단위·정의 정정 및 수정이력 공개", "품질KPI": "컬럼정의 일치율"},
            {"사례ID": "Q5", "유형": "현행화", "우선순위": "2", "확인된사례": "수급자·수급종료자 통계가 2020년 8월 기준 1회성", "분석영향": "최신 연도별 수급종료 흐름 분석 불가", "개선조치": "연도별 정기 갱신 또는 기준시점 명확화", "품질KPI": "현행화 준수율·갱신지연일수"},
            {"사례ID": "Q6", "유형": "정합성", "우선순위": "2", "확인된사례": "2025년 교원 퇴직자 14,789명과 퇴직사유 파일 14,193명", "분석영향": "퇴직사유 비중의 모집단 일반화 제한", "개선조치": "학교급 포함범위·누락/제외 기준 공개", "품질KPI": "교차자료 총계 설명률"},
            {"사례ID": "Q7", "유형": "단위", "우선순위": "1", "확인된사례": "평균연금월액 원값 최대 49,820,709원", "분석영향": "연령별 실제 연금수준 분석 보류", "개선조치": "단위·산식·원값 생성방식 확인·정정", "품질KPI": "단위 메타데이터 일치율"},
            {"사례ID": "Q8", "유형": "기준시점", "우선순위": "2", "확인된사례": "게시물 활용파일에 기준시점·게시일 없음", "분석영향": "기간별 활용성과 비교 불가", "개선조치": "기준일·게시일·집계기간 필드 추가", "품질KPI": "기준시점 기재율"},
        ]
    )


def build_gap_map() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"연구질문": "누가 디지털 서비스를 이용하는가", "현행자료": "가입 계정·일부 접수·상담 총량", "결측연결변수": "이용자구분·연령대", "현재판단": "불가", "필요지표": "집단별 이용률"},
            {"연구질문": "PC와 모바일 중 어디에서 이용하는가", "현행자료": "접수건수만 존재", "결측연결변수": "PC웹·모바일웹·앱", "현재판단": "불가", "필요지표": "기기별 이용·완료율"},
            {"연구질문": "인증은 어디에서 막히는가", "현행자료": "인증단계 통계 없음", "결측연결변수": "인증방법·시도·성공·실패·실패사유", "현재판단": "불가", "필요지표": "인증성공률·실패사유 비중"},
            {"연구질문": "업무를 끝까지 완료하는가", "현행자료": "일부 유형 접수 결과", "결측연결변수": "업무시작·완료·중도이탈·보완요청", "현재판단": "불가", "필요지표": "업무완료율·중도이탈률"},
            {"연구질문": "디지털 이용 후 상담으로 전환하는가", "현행자료": "상담 채널과 인터넷 접수가 별도 파일", "결측연결변수": "최초채널·최종채널·익명 사례키", "현재판단": "불가", "필요지표": "디지털→상담 전환율"},
            {"연구질문": "같은 문제로 반복 문의하는가", "현행자료": "연도별 처리·VOC 총량", "결측연결변수": "익명 사례키·재접촉 여부·처리결과", "현재판단": "불가", "필요지표": "반복상담률·재접촉률"},
            {"연구질문": "퇴직자가 언제 신규 수급자가 되는가", "현행자료": "퇴직자 유량·수급자 저량", "결측연결변수": "신규 수급개시·급여선택·수급종료 흐름", "현재판단": "불가", "필요지표": "신규수급개시율·종료율"},
        ]
    )


def make_pension_figure(frame: pd.DataFrame) -> None:
    plot = frame.iloc[::-1].reset_index(drop=True)
    labels = [f"ID {row['데이터ID']}  {row['자료구분']}" for _, row in plot.iterrows()]
    values = plot["2025값"].to_numpy()
    colors = [PURPLE, MID_BLUE, MID_BLUE, NAVY]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.barh(np.arange(len(plot)), values, color=colors, height=0.56)
    ax.set_yticks(np.arange(len(plot)), labels)
    ax.set_xlim(0, 125_000)
    ax.set_xlabel("공표 또는 부문합 수급자(명)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x/10000)}만" if x else "0"))
    for bar, value in zip(bars, values):
        ax.text(value + 1_200, bar.get_y() + bar.get_height()/2, f"{value:,}명", va="center", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("2025년 퇴직연금수급자 관련 공개값 비교", loc="left", color=NAVY, pad=28)
    ax.text(0, 1.025, "자료별 기준일·모집단·집계 정의 확인 전 하나의 총계로 통합하지 않음", transform=ax.transAxes, color=GRAY, fontsize=9.5)
    style_axis(ax)
    add_source(fig, "공공데이터포털 ID 15045820·15064966·15045815·15045816", "값 차이를 오류로 단정하지 않고 교차자료 이용 위험으로 진단")
    fig.subplots_adjust(left=0.31, right=0.94, top=0.79, bottom=0.16)
    save(fig, "13_2025년_퇴직연금수급자_공개값_비교.png")


def make_channel_difference_figure(recent: pd.DataFrame) -> None:
    years = recent["년도"].astype(int).to_numpy()
    values = recent["차이_채널합minus처리건수"].to_numpy()
    colors = [CORAL if v < 0 else BLUE for v in values]
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    bars = ax.bar(years, values, color=colors, width=0.58)
    ax.axhline(0, color=NAVY, linewidth=1.2)
    for bar, value in zip(bars, values):
        offset = 220 if value >= 0 else -260
        ax.text(bar.get_x()+bar.get_width()/2, value+offset, f"{value:+,}건", ha="center", va="bottom" if value >= 0 else "top", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_xticks(years)
    ax.set_ylabel("채널 부문 합-공표 처리건수(건)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_title("고객 상담 채널 합계 차이", loc="left", color=NAVY, pad=28)
    ax.text(0, 1.025, "2017~2022년은 일치, 2023~2025년은 공식 원본에서 차이 재현", transform=ax.transAxes, color=GRAY, fontsize=9.5)
    style_axis(ax, grid_axis="y")
    add_source(fig, "공공데이터포털 ID 15102547 ‘고객 상담 채널별 업무처리 현황’", "차이=온라인+전화+방문+기타-처리건수; 원인은 현재 자료로 확정하지 않음")
    fig.subplots_adjust(left=0.14, right=0.96, top=0.78, bottom=0.17)
    save(fig, "14_고객상담_채널합계_차이.png")


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    configure_plotting()

    pension_frame, pension_metrics = pension_totals()
    channel_frame, channel_metrics = channel_differences()
    date_metrics = date_quality()
    region_metrics = regional_columns()
    extra_metrics = supplementary_cases()

    catalog = pd.read_csv(CATALOG / "사학연금공단_공공데이터_186개_목록_20260831.csv", encoding="utf-8-sig")
    ended = catalog[catalog["데이터ID"] == 15063431].iloc[0]
    freshness = {
        "데이터ID": 15063431,
        "데이터명": ended["데이터명"],
        "설명상_기준": "2020년 8월",
        "포털수정일": str(ended["수정일"]),
        "로컬원본": "미보존; 메타데이터 목록만 보존",
        "판정": "최신 연도별 수급종료 흐름 분석에 사용할 수 없는 1회성 단면",
    }

    metrics = {
        "검증일": "2026-08-31",
        "분석공백_정의": "필요한 변수가 없거나 서로 연결되지 않아 연구질문을 계산할 수 없는 상태",
        "데이터품질_정의": "공개된 값의 합계·날짜·컬럼·단위·기준시점 설명이 일관되거나 충분하지 않은 상태",
        "퇴직연금수급자_공개값": pension_metrics,
        "상담채널_합계차이": channel_metrics,
        "연월표기": date_metrics,
        "75세지역파일": region_metrics,
        "수급종료자_현행화": freshness,
        "보조사례": extra_metrics,
    }
    quality = build_quality_cases(metrics)
    gaps = build_gap_map()
    quality.to_csv(PROCESSED / "공공데이터_품질진단_사례표.csv", index=False, encoding="utf-8-sig")
    gaps.to_csv(PROCESSED / "디지털고객서비스_분석공백_필드매핑.csv", index=False, encoding="utf-8-sig")
    pension_frame.to_csv(PROCESSED / "2025_퇴직연금수급자_공개값비교.csv", index=False, encoding="utf-8-sig")
    channel_frame.to_csv(PROCESSED / "고객상담_채널합계차이_2023_2025.csv", index=False, encoding="utf-8-sig")
    (EVIDENCE / "Ⅴ_분석공백_품질진단_검증_20260831.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    make_pension_figure(pension_frame)
    make_channel_difference_figure(channel_frame)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
