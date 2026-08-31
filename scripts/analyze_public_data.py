#!/usr/bin/env python3
"""사학연금 공개데이터 재현 분석 파이프라인.

원본 CSV를 변경하지 않고 품질검사, 정제 데이터, 핵심 지표, 그래프와
검증표를 생성한다. 입력 파일은 공공데이터포털에서 2026-08-31 확인한
2025-12-31 기준 공식 파일이다.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

TASK_CACHE = Path(tempfile.gettempdir()) / "tp-public-data-cache"
TASK_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TASK_CACHE / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TASK_CACHE / "xdg"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter, MaxNLocator


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "output" / "figures"
EVIDENCE = ROOT / "output" / "evidence"

RETIRE_FILE = RAW / "사립학교교직원연금공단_연도별_교직원_퇴직현황_20251231.csv"
PENSION_FILE = RAW / "사립학교교직원연금공단_연도별_연금수급자_및_연금액_20251231.csv"

SOURCE_RETIRE = "공공데이터포털, 사립학교교직원연금공단 ‘연도별 교직원 퇴직현황’(2025.12.31 기준)"
SOURCE_PENSION = "공공데이터포털, 사립학교교직원연금공단 ‘연도별 연금수급자 및 연금액’(2025.12.31 기준)"

NAVY = "#24364B"
BLUE = "#138ACB"
MID_BLUE = "#4C78A8"
PURPLE = "#7A6FA6"
LIGHT_BLUE = "#D9EDF7"
LIGHT_GRAY = "#EEF1F4"
GRAY = "#68737D"
CORAL = "#D66A5E"
INK = "#222222"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def configure_plotting() -> None:
    korean_font = Path("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/7a0b5c0f3c1d41c4c52a33343496c9c65ad52c50.asset/AssetData/NanumGothic.ttc")
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


def load_and_validate() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    for path in (RETIRE_FILE, PENSION_FILE):
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"원자료가 없거나 비어 있습니다: {path}")

    retire_raw = pd.read_csv(RETIRE_FILE, encoding="cp949")
    pension_raw = pd.read_csv(PENSION_FILE, encoding="cp949")

    expected_retire = {"연도", "교원", "직원"}
    expected_pension = {"연도", "퇴직연금 인원(명)", "퇴직연금 평균 연금액"}
    if not expected_retire.issubset(retire_raw.columns):
        raise ValueError(f"퇴직현황 필수 열 누락: {expected_retire - set(retire_raw.columns)}")
    if not expected_pension.issubset(pension_raw.columns):
        raise ValueError(f"수급자 자료 필수 열 누락: {expected_pension - set(pension_raw.columns)}")

    for name, df in (("퇴직현황", retire_raw), ("수급자", pension_raw)):
        if df["연도"].duplicated().any():
            raise ValueError(f"{name} 연도 중복 발견")
        if not df["연도"].is_monotonic_increasing:
            raise ValueError(f"{name} 연도가 오름차순이 아님")
        if df.isna().any().any():
            raise ValueError(f"{name} 결측값 발견")

    retire = retire_raw.rename(columns={"교원": "교원_퇴직자수", "직원": "사무직원_퇴직자수"}).copy()
    retire["전체_퇴직자수"] = retire["교원_퇴직자수"] + retire["사무직원_퇴직자수"]
    retire["전년대비_증감"] = retire["전체_퇴직자수"].diff()
    retire["전년대비_증감률_pct"] = retire["전체_퇴직자수"].pct_change() * 100

    # 세부 학교급·직종·성별 열의 합과 상위 총계 비교. 초기 연도 0은
    # 실제 0과 미집계가 구분되지 않아 세부구조 분석에는 사용하지 않는다.
    detail_cols = [c for c in retire_raw.columns if c not in {"연도", "교원", "직원"}]
    retire["세부열_합계"] = retire_raw[detail_cols].sum(axis=1)
    retire["상위총계와_세부합계_차이"] = retire["전체_퇴직자수"] - retire["세부열_합계"]

    pension = pension_raw.rename(
        columns={
            "퇴직연금 인원(명)": "퇴직연금수급자수",
            "퇴직연금 평균 연금액": "퇴직연금_평균연금액_원",
        }
    ).copy()
    pension["수급자_순증"] = pension["퇴직연금수급자수"].diff()
    pension["수급자_증감률_pct"] = pension["퇴직연금수급자수"].pct_change() * 100
    pension["평균연금액_만원"] = pension["퇴직연금_평균연금액_원"] / 10_000

    quality = {
        "raw_files": {
            str(RETIRE_FILE.relative_to(ROOT)): {"sha256": sha256(RETIRE_FILE), "rows": len(retire_raw), "columns": len(retire_raw.columns)},
            str(PENSION_FILE.relative_to(ROOT)): {"sha256": sha256(PENSION_FILE), "rows": len(pension_raw), "columns": len(pension_raw.columns)},
        },
        "periods": {
            "retirement": [int(retire["연도"].min()), int(retire["연도"].max())],
            "pension": [int(pension["연도"].min()), int(pension["연도"].max())],
            "common": [max(int(retire["연도"].min()), int(pension["연도"].min())), min(int(retire["연도"].max()), int(pension["연도"].max()))],
        },
        "duplicates": {"retirement_year": 0, "pension_year": 0},
        "missing_cells": {"retirement": 0, "pension": 0},
        "retirement_detail_sum_matches_top_total_years": int((retire["상위총계와_세부합계_차이"] == 0).sum()),
        "retirement_detail_sum_mismatch_years": retire.loc[retire["상위총계와_세부합계_차이"] != 0, "연도"].astype(int).tolist(),
        "interpretation_notes": [
            "퇴직자는 해당 연도의 발생량(flow), 퇴직연금수급자는 연도별 수급 중인 인원(stock)으로 서로 다른 지표다.",
            "수급자 순증은 전년 수급자 수와의 차이이며 신규 수급개시자 수가 아니다.",
            "평균연금액은 물가조정하지 않은 명목금액이다.",
            "퇴직현황 세부열의 초기 0은 실제 0과 미집계를 구분하기 어려워 학교급별 장기분석에서 제외한다.",
        ],
    }
    return retire, pension, quality


def cagr(start: float, end: float, years: int) -> float:
    return ((end / start) ** (1 / years) - 1) * 100


def compute_summary(retire: pd.DataFrame, pension: pd.DataFrame) -> dict:
    r0, r1 = retire.iloc[0], retire.iloc[-1]
    p0, p1 = pension.iloc[0], pension.iloc[-1]
    p_peak_net = pension.loc[pension["수급자_순증"].idxmax()]
    r_peak = retire.loc[retire["전체_퇴직자수"].idxmax()]
    common = retire[["연도", "전체_퇴직자수"]].merge(
        pension[["연도", "퇴직연금수급자수", "수급자_순증", "수급자_증감률_pct"]], on="연도", how="inner"
    )
    return {
        "retirement": {
            "start_year": int(r0["연도"]),
            "end_year": int(r1["연도"]),
            "start_total": int(r0["전체_퇴직자수"]),
            "end_total": int(r1["전체_퇴직자수"]),
            "end_teachers": int(r1["교원_퇴직자수"]),
            "end_staff": int(r1["사무직원_퇴직자수"]),
            "peak_year": int(r_peak["연도"]),
            "peak_total": int(r_peak["전체_퇴직자수"]),
            "latest_yoy_change": int(r1["전년대비_증감"]),
            "latest_yoy_rate_pct": round(float(r1["전년대비_증감률_pct"]), 2),
        },
        "pension": {
            "start_year": int(p0["연도"]),
            "end_year": int(p1["연도"]),
            "start_recipients": int(p0["퇴직연금수급자수"]),
            "end_recipients": int(p1["퇴직연금수급자수"]),
            "multiple": round(float(p1["퇴직연금수급자수"] / p0["퇴직연금수급자수"]), 2),
            "absolute_increase": int(p1["퇴직연금수급자수"] - p0["퇴직연금수급자수"]),
            "cagr_pct": round(cagr(float(p0["퇴직연금수급자수"]), float(p1["퇴직연금수급자수"]), int(p1["연도"] - p0["연도"])), 2),
            "latest_net_increase": int(p1["수급자_순증"]),
            "latest_growth_pct": round(float(p1["수급자_증감률_pct"]), 2),
            "peak_net_increase_year": int(p_peak_net["연도"]),
            "peak_net_increase": int(p_peak_net["수급자_순증"]),
        },
        "average_pension": {
            "start_won": int(p0["퇴직연금_평균연금액_원"]),
            "end_won": int(p1["퇴직연금_평균연금액_원"]),
            "nominal_change_pct": round((float(p1["퇴직연금_평균연금액_원"] / p0["퇴직연금_평균연금액_원"]) - 1) * 100, 2),
            "latest_yoy_change_won": int(pension["퇴직연금_평균연금액_원"].diff().iloc[-1]),
            "latest_yoy_rate_pct": round(float(pension["퇴직연금_평균연금액_원"].pct_change().iloc[-1] * 100), 2),
        },
        "common_period": {
            "start_year": int(common["연도"].min()),
            "end_year": int(common["연도"].max()),
            "years": len(common),
        },
    }


def style_axis(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#DDE3E8", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=9))


def save_figure(fig: plt.Figure, filename: str) -> None:
    path = FIGURES / filename
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def add_source(fig: plt.Figure, source: str, note: str | None = None) -> None:
    text = f"출처: {source}"
    if note:
        text += f"  |  주: {note}"
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=7.6, color=GRAY)


def make_figures(retire: pd.DataFrame, pension: pd.DataFrame) -> None:
    # 1. 연도별 퇴직자
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(retire["연도"], retire["전체_퇴직자수"], color=NAVY, lw=2.8, label="전체")
    ax.plot(retire["연도"], retire["교원_퇴직자수"], color=BLUE, lw=1.9, label="교원")
    ax.plot(retire["연도"], retire["사무직원_퇴직자수"], color=PURPLE, lw=1.9, label="사무직원(원자료 ‘직원’)")
    ax.scatter([retire.iloc[-1]["연도"]] * 3, [retire.iloc[-1][c] for c in ["전체_퇴직자수", "교원_퇴직자수", "사무직원_퇴직자수"]], color=[NAVY, BLUE, PURPLE], zorder=3)
    ax.set_title("연도별 전체·직종별 퇴직자 수", loc="left", color=NAVY, pad=14)
    ax.text(0, 1.02, "퇴직자는 해당 연도의 발생량(flow)이며 2025년 전체는 27,495명", transform=ax.transAxes, color=GRAY, fontsize=10)
    ax.set_ylabel("명")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.legend(ncol=3, loc="upper left")
    style_axis(ax)
    add_source(fig, SOURCE_RETIRE, "전체=교원+직원. 초기 세부 분류의 0은 장기 구조분석에 사용하지 않음")
    fig.subplots_adjust(bottom=0.16, top=0.82)
    save_figure(fig, "01_연도별_직종별_퇴직자_수.png")

    # 2. 퇴직연금수급자
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.fill_between(pension["연도"], pension["퇴직연금수급자수"], color=LIGHT_BLUE, alpha=0.85)
    ax.plot(pension["연도"], pension["퇴직연금수급자수"], color=NAVY, lw=2.8)
    ax.scatter([pension.iloc[0]["연도"], pension.iloc[-1]["연도"]], [pension.iloc[0]["퇴직연금수급자수"], pension.iloc[-1]["퇴직연금수급자수"]], color=BLUE, s=35, zorder=3)
    ax.annotate(f"{int(pension.iloc[0]['퇴직연금수급자수']):,}명", (pension.iloc[0]["연도"], pension.iloc[0]["퇴직연금수급자수"]), xytext=(8, 8), textcoords="offset points", fontsize=9)
    ax.annotate(f"{int(pension.iloc[-1]['퇴직연금수급자수']):,}명", (pension.iloc[-1]["연도"], pension.iloc[-1]["퇴직연금수급자수"]), xytext=(-4, 10), ha="right", textcoords="offset points", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("퇴직연금수급자 수의 장기 변화", loc="left", color=NAVY, pad=14)
    ax.text(0, 1.02, "1997년 4,997명에서 2025년 111,389명으로 22.3배", transform=ax.transAxes, color=GRAY, fontsize=10)
    ax.set_ylabel("명")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    style_axis(ax)
    add_source(fig, SOURCE_PENSION, "연도별 수급 중인 인원(stock)")
    fig.subplots_adjust(bottom=0.16, top=0.82)
    save_figure(fig, "02_퇴직연금수급자_추이.png")

    # 3. 순증과 증감률
    d = pension.dropna(subset=["수급자_순증"]).copy()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7.2), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
    colors = np.where(d["수급자_순증"] >= 0, MID_BLUE, CORAL)
    ax1.bar(d["연도"], d["수급자_순증"], color=colors, width=0.72)
    ax1.axhline(0, color="#8D969E", lw=0.9)
    ax1.set_title("퇴직연금수급자 전년 대비 순증과 증감률", loc="left", color=NAVY, pad=14)
    ax1.text(0, 1.02, "순증에는 신규 수급개시와 수급종료·전환·정정 등이 함께 반영됨", transform=ax1.transAxes, color=GRAY, fontsize=10)
    ax1.set_ylabel("순증(명)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    style_axis(ax1)
    ax2.plot(d["연도"], d["수급자_증감률_pct"], color=PURPLE, marker="o", ms=3.2, lw=1.8)
    ax2.axhline(0, color="#8D969E", lw=0.9)
    ax2.set_ylabel("증감률(%)")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}%"))
    style_axis(ax2)
    add_source(fig, SOURCE_PENSION, "순증=당해연도 수급자 수-전년도 수급자 수; 신규 수급자 수가 아님")
    fig.subplots_adjust(bottom=0.12, top=0.88, hspace=0.32)
    save_figure(fig, "03_퇴직연금수급자_순증_증감률.png")

    # 4. 평균연금액
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(pension["연도"], pension["평균연금액_만원"], color=NAVY, lw=2.8)
    ax.fill_between(pension["연도"], pension["평균연금액_만원"], color=LIGHT_GRAY, alpha=0.9)
    ax.scatter([pension.iloc[0]["연도"], pension.iloc[-1]["연도"]], [pension.iloc[0]["평균연금액_만원"], pension.iloc[-1]["평균연금액_만원"]], color=BLUE, s=35, zorder=3)
    ax.annotate(f"{pension.iloc[0]['평균연금액_만원']:.1f}만원", (pension.iloc[0]["연도"], pension.iloc[0]["평균연금액_만원"]), xytext=(8, 8), textcoords="offset points", fontsize=9)
    ax.annotate(f"{pension.iloc[-1]['평균연금액_만원']:.1f}만원", (pension.iloc[-1]["연도"], pension.iloc[-1]["평균연금액_만원"]), xytext=(-4, 10), ha="right", textcoords="offset points", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("퇴직연금 평균연금액의 장기 변화", loc="left", color=NAVY, pad=14)
    ax.text(0, 1.02, "물가를 조정하지 않은 명목금액으로 실질 구매력 변화를 뜻하지 않음", transform=ax.transAxes, color=GRAY, fontsize=10)
    ax.set_ylabel("만원")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    style_axis(ax)
    add_source(fig, SOURCE_PENSION, "원자료 금액을 10,000으로 나누어 만원 단위로 표시")
    fig.subplots_adjust(bottom=0.16, top=0.82)
    save_figure(fig, "04_퇴직연금_평균연금액_추이.png")

    # 5. 흐름과 저량 변화 비교
    comp = retire[["연도", "전체_퇴직자수"]].merge(pension[["연도", "수급자_순증"]], on="연도", how="inner").dropna()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7.0), sharex=True)
    ax1.plot(comp["연도"], comp["전체_퇴직자수"], color=BLUE, lw=2.4)
    ax1.set_ylabel("퇴직자(명)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax1.set_title("연간 퇴직자 수와 퇴직연금수급자 순증 비교", loc="left", color=NAVY, pad=14)
    ax1.text(0, 1.02, "단위는 같지만 개념이 달라 동일인 전환율이나 인과관계로 해석할 수 없음", transform=ax1.transAxes, color=GRAY, fontsize=10)
    style_axis(ax1)
    ax2.bar(comp["연도"], comp["수급자_순증"], color=PURPLE, width=0.72)
    ax2.axhline(0, color="#8D969E", lw=0.9)
    ax2.set_ylabel("수급자 순증(명)")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    style_axis(ax2)
    add_source(fig, f"{SOURCE_RETIRE}; {SOURCE_PENSION}", "공통기간 1998~2025년")
    fig.subplots_adjust(bottom=0.12, top=0.88, hspace=0.28)
    save_figure(fig, "05_퇴직자와_수급자순증_비교.png")


def write_outputs(retire: pd.DataFrame, pension: pd.DataFrame, quality: dict, summary: dict) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    retire.to_csv(PROCESSED / "연도별_교직원_퇴직현황_정제.csv", index=False, encoding="utf-8-sig")
    pension.to_csv(PROCESSED / "연도별_퇴직연금수급자_연금액_정제.csv", index=False, encoding="utf-8-sig")

    common = retire[["연도", "교원_퇴직자수", "사무직원_퇴직자수", "전체_퇴직자수"]].merge(
        pension[["연도", "퇴직연금수급자수", "수급자_순증", "수급자_증감률_pct", "퇴직연금_평균연금액_원"]], on="연도", how="inner"
    )
    common.to_csv(PROCESSED / "핵심지표_공통기간_1997_2025.csv", index=False, encoding="utf-8-sig")

    (PROCESSED / "quality_checks.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    (PROCESSED / "analysis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    dictionary = pd.DataFrame(
        [
            ["연도", "연도", "공통", "연간", "관측연도"],
            ["교원_퇴직자수", "명", "퇴직현황", "연간 발생량", "원자료 ‘교원’"],
            ["사무직원_퇴직자수", "명", "퇴직현황", "연간 발생량", "원자료 ‘직원’; 보고서에서는 사무직원으로 표기"],
            ["전체_퇴직자수", "명", "파생", "연간 발생량", "교원_퇴직자수+사무직원_퇴직자수"],
            ["퇴직연금수급자수", "명", "수급자", "연도별 저량", "원자료 ‘퇴직연금 인원(명)’"],
            ["수급자_순증", "명", "파생", "전년 대비 변화", "당해연도 수급자수-전년도 수급자수; 신규 수급자 수 아님"],
            ["수급자_증감률_pct", "%", "파생", "전년 대비 변화율", "(당해-전년)/전년×100"],
            ["퇴직연금_평균연금액_원", "원", "수급자", "명목금액", "원자료 ‘퇴직연금 평균 연금액’; 물가 미조정"],
        ],
        columns=["변수명", "단위", "출처구분", "통계성격", "정의·주의"],
    )
    dictionary.to_csv(PROCESSED / "데이터사전.csv", index=False, encoding="utf-8-sig")

    q = quality
    s = summary
    verification = f"""# 상상이상 사학연금 공개데이터 분석 수치검증표

- 검증일: 2026-08-31
- 분석 코드: `scripts/analyze_public_data.py`
- 원자료는 수정하지 않고 CP949로 읽은 뒤 정제 결과를 UTF-8-SIG로 별도 저장했다.

## 원자료 무결성

| 파일 | 행×열 | SHA-256 |
|---|---:|---|
| 연도별 교직원 퇴직현황 | {q['raw_files'][str(RETIRE_FILE.relative_to(ROOT))]['rows']}×{q['raw_files'][str(RETIRE_FILE.relative_to(ROOT))]['columns']} | `{q['raw_files'][str(RETIRE_FILE.relative_to(ROOT))]['sha256']}` |
| 연도별 연금수급자 및 연금액 | {q['raw_files'][str(PENSION_FILE.relative_to(ROOT))]['rows']}×{q['raw_files'][str(PENSION_FILE.relative_to(ROOT))]['columns']} | `{q['raw_files'][str(PENSION_FILE.relative_to(ROOT))]['sha256']}` |

## 핵심 수치

| 지표 | 검증값 | 산식·확인 |
|---|---:|---|
| 2025년 전체 퇴직자 | {s['retirement']['end_total']:,}명 | 교원 {s['retirement']['end_teachers']:,}+사무직원 {s['retirement']['end_staff']:,} |
| 퇴직자 최고 연도 | {s['retirement']['peak_year']}년 {s['retirement']['peak_total']:,}명 | 연도별 전체 최댓값 |
| 2025년 퇴직자 전년 대비 | {s['retirement']['latest_yoy_change']:+,}명 ({s['retirement']['latest_yoy_rate_pct']:+.2f}%) | 2025-2024 |
| 퇴직연금수급자 | {s['pension']['start_year']}년 {s['pension']['start_recipients']:,}명 → {s['pension']['end_year']}년 {s['pension']['end_recipients']:,}명 | {s['pension']['multiple']:.2f}배, 연평균 {s['pension']['cagr_pct']:.2f}% |
| 2025년 수급자 순증 | {s['pension']['latest_net_increase']:+,}명 ({s['pension']['latest_growth_pct']:+.2f}%) | 2025 수급자-2024 수급자; 신규 수급자 수 아님 |
| 최대 수급자 순증 | {s['pension']['peak_net_increase_year']}년 {s['pension']['peak_net_increase']:+,}명 | 전년 대비 차이 최댓값 |
| 퇴직연금 평균연금액 | {s['average_pension']['start_won']:,}원 → {s['average_pension']['end_won']:,}원 | 명목 {s['average_pension']['nominal_change_pct']:+.2f}%; 물가 미조정 |

## 품질검사 결과

- 연도 중복: 없음
- 결측값: 없음
- 기간: 퇴직현황 {q['periods']['retirement'][0]}~{q['periods']['retirement'][1]}년, 수급자·연금액 {q['periods']['pension'][0]}~{q['periods']['pension'][1]}년
- 세부열 합계가 상위 총계와 정확히 일치한 연도: {q['retirement_detail_sum_matches_top_total_years']}개년
- 불일치 연도: {q['retirement_detail_sum_mismatch_years']}
- 불일치는 초기 세부 분류의 0이 실제 0인지 미집계인지 구분되지 않는 문제를 포함하므로, 장기 퇴직자 분석은 상위 총계인 `교원`, `직원` 열만 사용했다.

## 해석 제한

1. 퇴직자는 연간 발생량(flow), 수급자는 연도별 수급 중인 인원(stock)이다.
2. 수급자 순증에는 신규 수급개시와 수급종료, 전환·정정 등이 함께 반영된다.
3. 평균연금액은 명목금액이며 실질 구매력 변화로 해석하지 않는다.
4. 집계 시계열의 동반 변화만으로 퇴직자 증가가 수급자 증가를 일으켰다고 단정하지 않는다.
"""
    (EVIDENCE / "Ⅲ_퇴직자·수급자_변화분석_수치검증.md").write_text(verification, encoding="utf-8")


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    configure_plotting()
    retire, pension, quality = load_and_validate()
    summary = compute_summary(retire, pension)
    write_outputs(retire, pension, quality, summary)
    make_figures(retire, pension)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
