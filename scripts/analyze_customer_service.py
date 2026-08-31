#!/usr/bin/env python3
"""Ⅳ장 현행 디지털 고객서비스 공개데이터를 재현·검증하고 그래프를 만든다.

원본 CSV는 덮어쓰지 않는다. 공공데이터포털 다운로드 과정에서 뒤집힌
연월은 분석용 파생변수로만 복원한다.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "catalog_audit"
PROCESSED = ROOT / "data" / "processed"
EVIDENCE = ROOT / "output" / "evidence"
FIGURES = ROOT / "output" / "figures" / "verified"

TASK_CACHE = Path(tempfile.gettempdir()) / "tp-customer-service-cache"
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
LIGHT_BLUE = "#D9EDF7"
PURPLE = "#7A6FA6"
CORAL = "#D66A5E"
GOLD = "#C9952E"
GREEN = "#4C956C"
GRAY = "#68737D"
LIGHT_GRAY = "#E8EDF1"
INK = "#222222"


def read(dataset_id: int) -> pd.DataFrame:
    return pd.read_csv(RAW / f"{dataset_id}.csv", encoding="cp949")


def restore_portal_year_month(series: pd.Series) -> pd.Series:
    """공표 CSV의 2025-MM-YY 표기를 실제 YYYY-MM의 월초로 복원한다."""
    parsed = pd.to_datetime(series, errors="raise")
    return pd.to_datetime(
        {"year": 2000 + parsed.dt.day, "month": parsed.dt.month, "day": 1}
    )


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


def style_axis(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid_axis, color="#DDE3E8", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)


def add_source(fig: plt.Figure, source: str, note: str) -> None:
    fig.text(
        0.01,
        0.01,
        f"출처: {source}  |  주: {note}",
        ha="left",
        va="bottom",
        fontsize=7.1,
        color=GRAY,
    )


def save(fig: plt.Figure, filename: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / filename, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def prepare_website() -> tuple[pd.DataFrame, dict]:
    website = read(15065011)
    website["복원_기준연월"] = restore_portal_year_month(website["기준연월"])
    website = website.sort_values("복원_기준연월")
    website["연도"] = website["복원_기준연월"].dt.year
    website["월"] = website["복원_기준연월"].dt.month
    annual = website.groupby("연도", as_index=False).agg(
        월수=("월", "count"),
        연말_가입인원수=("가입인원수", "last"),
        연간_신규가입인원수=("신규가입인원수", "sum"),
    )
    annual["연말가입인원_전년차"] = annual["연말_가입인원수"].diff()
    annual["연말증가와_연간신규합_차이"] = (
        annual["연말가입인원_전년차"] - annual["연간_신규가입인원수"]
    )
    assert annual.loc[annual["연도"].between(2021, 2025), "연말증가와_연간신규합_차이"].eq(0).all()

    complete = annual[annual["연도"].between(2020, 2025)].copy()
    first = int(website.iloc[0]["가입인원수"])
    last_2025 = int(complete.loc[complete["연도"] == 2025, "연말_가입인원수"].iloc[0])
    metrics = {
        "원본행수": int(len(website)),
        "복원기간": f"{website['복원_기준연월'].min():%Y-%m}~{website['복원_기준연월'].max():%Y-%m}",
        "완전연도_그래프기간": "2020~2025",
        "2020년1월_가입인원": first,
        "2025년12월_가입인원": last_2025,
        "2020년1월대비_증가": last_2025 - first,
        "2020년1월대비_증가율_pct": round((last_2025 / first - 1) * 100, 4),
        "2025년_신규가입합": int(complete.loc[complete["연도"] == 2025, "연간_신규가입인원수"].iloc[0]),
        "2024년_신규가입합": int(complete.loc[complete["연도"] == 2024, "연간_신규가입인원수"].iloc[0]),
        "2026년은_부분기간": "1~5월",
    }
    return annual, metrics


def prepare_channels() -> tuple[pd.DataFrame, dict]:
    channel = read(15102547)
    parts = ["등록채널(온라인)", "등록채널(전화)", "등록채널(방문)", "등록채널(기타)"]
    channel["채널부문합계"] = channel[parts].sum(axis=1)
    channel["합계차이_채널부문minus처리건수"] = channel["채널부문합계"] - channel["처리건수"]
    for column in parts:
        channel[f"{column}_비중_pct"] = channel[column] / channel["채널부문합계"] * 100
    mismatch = channel[channel["합계차이_채널부문minus처리건수"] != 0]
    assert mismatch["년도"].tolist() == [2023, 2024, 2025]
    row = channel[channel["년도"] == 2025].iloc[0]
    metrics = {
        "기간": "2017~2025",
        "2025_공표처리건수": int(row["처리건수"]),
        "2025_채널부문합계": int(row["채널부문합계"]),
        "2025_전화건수": int(row["등록채널(전화)"]),
        "2025_전화비중_pct": round(float(row["등록채널(전화)_비중_pct"]), 4),
        "2025_온라인건수": int(row["등록채널(온라인)"]),
        "2025_온라인비중_pct": round(float(row["등록채널(온라인)_비중_pct"]), 4),
        "합계불일치": {
            str(int(r["년도"])): int(r["합계차이_채널부문minus처리건수"])
            for _, r in mismatch.iterrows()
        },
        "비중산식": "해당 채널 건수÷온라인·전화·방문·기타 합×100",
    }
    return channel, metrics


def prepare_voc() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    voc = read(15133677)
    categories = [c for c in voc.columns if c not in {"연도", "합계"}]
    voc["VOC부문합계"] = voc[categories].sum(axis=1)
    voc["VOC내부합계차이"] = voc["VOC부문합계"] - voc["합계"]
    assert voc["VOC내부합계차이"].eq(0).all()

    monthly_top = read(15124513)
    monthly_top["연도"] = monthly_top["연월"].str[:4].astype(int)
    monthly_categories = [c for c in monthly_top.columns if c not in {"연월", "연도"}]
    selected_annual = monthly_top.groupby("연도", as_index=False)[monthly_categories].sum()
    selected_annual["상위민원선별합"] = selected_annual[monthly_categories].sum(axis=1)
    cross = voc[["연도", "합계"]].merge(
        selected_annual[["연도", "상위민원선별합"]], on="연도", how="left"
    )
    cross["전체VOC대비_선별집합_pct"] = cross["상위민원선별합"] / cross["합계"] * 100

    row_2019 = voc[voc["연도"] == 2019].iloc[0]
    row_2024 = voc[voc["연도"] == 2024].iloc[0]
    row_2025 = voc[voc["연도"] == 2025].iloc[0]
    top5 = sorted(categories, key=lambda c: row_2025[c], reverse=True)[:5]
    top5_total = int(row_2025[top5].sum())
    metrics = {
        "기간": "2019~2025",
        "내부합계일치": True,
        "2019_합계": int(row_2019["합계"]),
        "2024_합계": int(row_2024["합계"]),
        "2025_합계": int(row_2025["합계"]),
        "2019대비2025_증감": int(row_2025["합계"] - row_2019["합계"]),
        "2019대비2025_증감률_pct": round((row_2025["합계"] / row_2019["합계"] - 1) * 100, 4),
        "2024대비2025_증감": int(row_2025["합계"] - row_2024["합계"]),
        "2024대비2025_증감률_pct": round((row_2025["합계"] / row_2024["합계"] - 1) * 100, 4),
        "2025_상위5개": {
            category: {
                "건수": int(row_2025[category]),
                "비중_pct": round(float(row_2025[category] / row_2025["합계"] * 100), 4),
            }
            for category in top5
        },
        "2025_상위5개합": top5_total,
        "2025_상위5개비중_pct": round(top5_total / row_2025["합계"] * 100, 4),
        "월별상위민원_전체VOC대비범위_pct": [
            round(float(cross["전체VOC대비_선별집합_pct"].min()), 4),
            round(float(cross["전체VOC대비_선별집합_pct"].max()), 4),
        ],
        "월별상위민원_주의": "2013~2024 선별 집합이며 전체 VOC가 아님",
    }
    return voc, cross, metrics


def prepare_internet() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    internet = read(15151198)
    internet["복원_요청연월"] = restore_portal_year_month(internet["요청년월"])
    internet["연도"] = internet["복원_요청연월"].dt.year
    internet["월"] = internet["복원_요청연월"].dt.month
    by_type = (
        internet.groupby(["연도", "신청구분코드", "신청구분명"], as_index=False)["접수건수"]
        .sum()
        .sort_values(["연도", "신청구분코드"])
    )
    recent = by_type[by_type["연도"].between(2021, 2025)].copy()
    recent_totals = recent.groupby("연도")["접수건수"].sum()
    type_totals = internet.groupby(["신청구분코드", "신청구분명"])["접수건수"].sum()
    row_2025 = recent[recent["연도"] == 2025].groupby("신청구분명")["접수건수"].sum()
    metrics = {
        "원본행수": int(len(internet)),
        "복원기간": f"{internet['복원_요청연월'].min():%Y-%m}~{internet['복원_요청연월'].max():%Y-%m}",
        "신청유형수": int(internet["신청구분명"].nunique()),
        "전체기간_접수건수": int(internet["접수건수"].sum()),
        "그래프기간": "2021~2025 완전연도",
        "2021_접수건수": int(recent_totals.loc[2021]),
        "2024_접수건수": int(recent_totals.loc[2024]),
        "2025_접수건수": int(recent_totals.loc[2025]),
        "2021대비2025_증감률_pct": round((recent_totals.loc[2025] / recent_totals.loc[2021] - 1) * 100, 4),
        "2024대비2025_증감률_pct": round((recent_totals.loc[2025] / recent_totals.loc[2024] - 1) * 100, 4),
        "2025_유형별": {
            name: {
                "건수": int(value),
                "비중_pct": round(float(value / recent_totals.loc[2025] * 100), 4),
            }
            for name, value in row_2025.sort_values(ascending=False).items()
        },
        "전체기간_유형별": {
            f"{code}_{name}": int(value) for (code, name), value in type_totals.items()
        },
        "부분연도_제외": "2006년은 10~12월, 2026년은 1~4월이므로 최근 완전연도 그래프에서 제외",
    }
    return by_type, recent, metrics


def prepare_posts() -> tuple[pd.DataFrame, dict]:
    posts = read(15151262)
    count_columns = [c for c in posts.columns if c.endswith("건수")]
    posts["공표활용건수합"] = posts[count_columns].sum(axis=1)
    totals = posts[count_columns].sum()
    metrics = {
        "원본행수": int(len(posts)),
        "게시판분류수": int(posts["게시판분류"].nunique()),
        "게시물제목중복행수": int(posts["게시물제목"].duplicated().sum()),
        "공표활용건수합": int(totals.sum()),
        "항목별합": {column: int(value) for column, value in totals.items()},
        "기준시점컬럼": "없음",
        "해석한계": "게시물 공유 클릭·다운로드 등 콘텐츠 반응 자료이며 로그인·인증·업무완료 자료가 아님",
    }
    board = (
        posts.groupby("게시판분류", as_index=False)[count_columns + ["공표활용건수합"]]
        .sum()
        .sort_values("공표활용건수합", ascending=False)
    )
    return board, metrics


def make_website_figure(annual: pd.DataFrame) -> None:
    plot = annual[annual["연도"].between(2020, 2025)].copy()
    years = plot["연도"].to_numpy()
    stock = plot["연말_가입인원수"].to_numpy()
    new = plot["연간_신규가입인원수"].to_numpy()

    fig, axes = plt.subplots(2, 1, figsize=(10, 7.2), sharex=True, gridspec_kw={"height_ratios": [1.15, 1]})
    ax1, ax2 = axes
    ax1.plot(years, stock, color=NAVY, linewidth=2.8, marker="o", markersize=7)
    for year, value in zip(years, stock):
        ax1.annotate(f"{value/10000:.1f}만", (year, value), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9, color=NAVY)
    ax1.set_ylabel("연말 가입인원(명)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/10000:.0f}만"))
    style_axis(ax1)

    bars = ax2.bar(years, new, color=BLUE, width=0.58)
    for bar, value in zip(bars, new):
        ax2.text(bar.get_x() + bar.get_width()/2, value + 600, f"{value:,}", ha="center", va="bottom", fontsize=8.5)
    ax2.set_ylabel("연간 신규가입 합(명)")
    ax2.set_xticks(years)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    style_axis(ax2)

    fig.suptitle("홈페이지 가입인원과 연간 신규가입 변화", x=0.01, ha="left", color=NAVY, fontsize=16, fontweight="bold")
    fig.text(0.01, 0.925, "완전연도 2020~2025 기준 — 가입 계정 규모이며 접속자·활성이용자가 아님", color=GRAY, fontsize=10)
    add_source(fig, "공공데이터포털 ID 15065011 ‘월별 홈페이지 가입자 현황’", "원본 2025-MM-YY 표기를 YYYY-MM로 복원; 2026년 1~5월은 그래프 제외")
    fig.subplots_adjust(left=0.11, right=0.96, top=0.86, bottom=0.11, hspace=0.25)
    save(fig, "09_홈페이지가입자_변화.png")


def make_channel_figure(channel: pd.DataFrame) -> None:
    years = channel["년도"].to_numpy()
    phone = channel["등록채널(전화)"].to_numpy()
    online = channel["등록채널(온라인)"].to_numpy()
    visit = channel["등록채널(방문)"].to_numpy()
    other = channel["등록채널(기타)"].to_numpy()

    fig, axes = plt.subplots(2, 1, figsize=(10, 7.3), sharex=True, gridspec_kw={"height_ratios": [1.12, 1]})
    ax1, ax2 = axes
    ax1.plot(years, phone, color=NAVY, linewidth=2.8, marker="o", markersize=5.5, label="전화")
    ax1.fill_between(years, phone, color=LIGHT_BLUE, alpha=0.55)
    ax1.set_ylabel("전화(건)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/10000:.0f}만"))
    ax1.annotate(f"2025  {phone[-1]:,}건", (years[-1], phone[-1]), xytext=(-10, -22), textcoords="offset points", ha="right", fontsize=9, color=NAVY, fontweight="bold")
    style_axis(ax1)

    ax2.plot(years, online, color=BLUE, linewidth=2.4, marker="o", label="온라인")
    ax2.plot(years, visit, color=CORAL, linewidth=2, marker="o", label="방문")
    ax2.plot(years, other, color=GRAY, linewidth=1.8, marker="o", label="기타")
    ax2.set_ylabel("비전화 채널(건)")
    ax2.set_xticks(years)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax2.legend(loc="upper right", ncol=3)
    style_axis(ax2)

    fig.suptitle("고객 상담 채널별 처리 규모", x=0.01, ha="left", color=NAVY, fontsize=16, fontweight="bold")
    fig.text(0.01, 0.925, "2025년 채널 부문 합 기준 전화 99.25%, 온라인 0.75%", color=GRAY, fontsize=10)
    add_source(fig, "공공데이터포털 ID 15102547 ‘고객 상담 채널별 업무처리 현황’", "비중 분모는 4개 채널 합; 채널 합-공표 처리건수 차이 2023 -526, 2024 +8,967, 2025 -44건")
    fig.subplots_adjust(left=0.11, right=0.96, top=0.86, bottom=0.11, hspace=0.24)
    save(fig, "10_고객상담_채널별_추이.png")


def make_voc_figure(voc: pd.DataFrame, top5: list[str]) -> None:
    colors = [NAVY, BLUE, CORAL, PURPLE, GREEN]
    label_offsets = {"아웃바운드": 0, "대여": 10, "급여": -10, "연금수급자": 0, "가입자관리": 0}
    years = voc["연도"].to_numpy()
    fig, ax = plt.subplots(figsize=(10, 6.1))
    for category, color in zip(top5, colors):
        values = voc[category].to_numpy()
        ax.plot(years, values, linewidth=2.3, marker="o", markersize=5.5, label=category, color=color)
        ax.annotate(
            f"{values[-1]:,}",
            (years[-1], values[-1]),
            xytext=(8, label_offsets.get(category, 0)),
            textcoords="offset points",
            va="center",
            fontsize=8.5,
            color=color,
        )
    ax.set_xticks(years)
    ax.set_ylabel("VOC 건수(건)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x/10000)}만" if x >= 10000 else f"{int(x):,}"))
    ax.set_xlim(years.min(), years.max() + 0.45)
    ax.legend(loc="upper center", ncol=5, bbox_to_anchor=(0.5, -0.12))
    ax.set_title("주요 업무구분별 VOC 추이", loc="left", color=NAVY, pad=28)
    ax.text(0, 1.025, "2025년 건수 상위 5개 업무의 2019~2025년 변화", transform=ax.transAxes, color=GRAY, fontsize=10)
    style_axis(ax)
    add_source(fig, "공공데이터포털 ID 15133677 ‘업무구분별 VOC 현황’", "연도별 15개 부문 합과 공표 합계는 일치; VOC 건수를 고객 불만·상담 처리건수와 동일시하지 않음")
    fig.subplots_adjust(left=0.11, right=0.91, top=0.84, bottom=0.22)
    save(fig, "11_주요업무구분별_VOC_추이.png")


def make_internet_figure(recent: pd.DataFrame) -> None:
    pivot = recent.pivot_table(index="연도", columns="신청구분명", values="접수건수", aggfunc="sum", fill_value=0)
    years = np.arange(2021, 2026)
    pivot = pivot.reindex(years, fill_value=0)
    groups = pd.DataFrame(index=years)
    groups["연금수급자정보변경"] = pivot.get("연금수급자정보변경", 0)
    groups["연금수급증발급"] = pivot.get("연금수급증발급", 0)
    groups["미구분"] = pivot.get("미구분", 0)
    named_other = [c for c in pivot.columns if c not in groups.columns]
    groups["기타 명시 유형"] = pivot[named_other].sum(axis=1) if named_other else 0

    fig, ax = plt.subplots(figsize=(10, 5.9))
    bottom = np.zeros(len(years))
    colors = [NAVY, BLUE, GOLD, LIGHT_GRAY]
    for category, color in zip(groups.columns, colors):
        values = groups[category].to_numpy()
        ax.bar(years, values, bottom=bottom, label=category, color=color, width=0.62)
        bottom += values
    for year, total in zip(years, bottom):
        ax.text(year, total + 28, f"{int(total):,}", ha="center", va="bottom", fontsize=9, fontweight="bold", color=NAVY)
    ax.set_xticks(years)
    ax.set_ylabel("접수건수(건)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_ylim(0, max(bottom) * 1.18)
    ax.legend(loc="upper left", ncol=2)
    ax.set_title("인터넷 접수 유형별 최근 5년 변화", loc="left", color=NAVY, pad=28)
    ax.text(0, 1.025, "연월 복원 후 완전연도 2021~2025 기준", transform=ax.transAxes, color=GRAY, fontsize=10)
    style_axis(ax)
    add_source(fig, "공공데이터포털 ID 15151198 ‘인터넷 접수 현황’", "원본 2025-MM-YY를 YYYY-MM로 복원; 기타 명시 유형=신분변동·정지 관련 2종·청산일시금")
    fig.subplots_adjust(left=0.11, right=0.96, top=0.82, bottom=0.15)
    save(fig, "12_인터넷접수_최근5년_유형별.png")


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    configure_plotting()

    website, website_metrics = prepare_website()
    channels, channel_metrics = prepare_channels()
    voc, voc_cross, voc_metrics = prepare_voc()
    internet_by_type, internet_recent, internet_metrics = prepare_internet()
    post_board, post_metrics = prepare_posts()

    website.to_csv(PROCESSED / "홈페이지가입자_연도별_정제.csv", index=False, encoding="utf-8-sig")
    channels.to_csv(PROCESSED / "고객상담_채널별_정제.csv", index=False, encoding="utf-8-sig")
    voc.to_csv(PROCESSED / "VOC_업무구분별_정제.csv", index=False, encoding="utf-8-sig")
    voc_cross.to_csv(PROCESSED / "VOC상위민원_전체VOC_비교.csv", index=False, encoding="utf-8-sig")
    internet_by_type.to_csv(PROCESSED / "인터넷접수_연도유형별_정제.csv", index=False, encoding="utf-8-sig")
    post_board.to_csv(PROCESSED / "대표홈페이지게시물활용_게시판별_요약.csv", index=False, encoding="utf-8-sig")

    top5 = list(voc_metrics["2025_상위5개"].keys())
    make_website_figure(website)
    make_channel_figure(channels)
    make_voc_figure(voc, top5)
    make_internet_figure(internet_recent)

    evidence = {
        "검증일": "2026-08-31",
        "홈페이지가입자_15065011": website_metrics,
        "고객상담채널_15102547": channel_metrics,
        "업무구분별VOC_15133677": voc_metrics,
        "인터넷접수_15151198": internet_metrics,
        "대표홈페이지게시물활용_15151262": post_metrics,
        "공통금지해석": [
            "홈페이지 가입인원을 접속자·활성이용자·업무완료자로 표현하지 않는다.",
            "상담 전화 비중을 고령층의 디지털 불편 또는 인증 실패 원인으로 단정하지 않는다.",
            "VOC 건수를 고객 상담 처리건수 또는 불만 건수와 동일시하지 않는다.",
            "인터넷 접수 7개 유형을 전체 디지털 서비스 이용량으로 일반화하지 않는다.",
            "게시물 활용건수를 로그인·인증·민원 업무완료 성과로 표현하지 않는다.",
        ],
    }
    path = EVIDENCE / "Ⅳ_현행_디지털고객서비스_수치검증_20260831.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
