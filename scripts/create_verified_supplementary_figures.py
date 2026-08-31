#!/usr/bin/env python3
"""공식 원자료만으로 중복 없는 보고서 보조 그래프 3종을 생성한다."""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path


TASK_CACHE = Path(tempfile.gettempdir()) / "tp-supplementary-figures-cache"
TASK_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TASK_CACHE / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TASK_CACHE / "xdg"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
TEAM_RAW = ROOT / "data" / "raw" / "team_contributed"
FIGURES = ROOT / "output" / "figures" / "verified"
EVIDENCE = ROOT / "output" / "evidence" / "추가그래프_검증값_20260831.json"

NAVY = "#24364B"
BLUE = "#138ACB"
MID_BLUE = "#4C78A8"
PURPLE = "#7A6FA6"
LIGHT_BLUE = "#D9EDF7"
GRAY = "#68737D"
LIGHT_GRAY = "#EEF1F4"
CORAL = "#D66A5E"
INK = "#222222"


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def find_csv(keyword: str) -> Path:
    matches = [path for path in TEAM_RAW.glob("*.csv") if keyword in nfc(path.name)]
    if len(matches) != 1:
        raise RuntimeError(f"{keyword!r} CSV를 하나로 특정하지 못함: {matches}")
    return matches[0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="cp949", newline="") as handle:
        return list(csv.DictReader(handle))


def integer(value: str | None) -> int:
    if value is None or value.strip() == "":
        return 0
    return int(float(value))


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
    fig.text(0.01, 0.01, f"출처: {source}  |  주: {note}", ha="left", va="bottom", fontsize=7.3, color=GRAY)


def save(fig: plt.Figure, filename: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / filename, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_ratio_figure() -> dict:
    # 사학연금공단 홈페이지 '연도별 가입 현황', 2026-08-31 확인.
    years = np.array([2021, 2022, 2023, 2024, 2025])
    subscribers = np.array([330_322, 333_231, 333_852, 323_542, 332_359])
    recipients = np.array([98_730, 106_896, 115_224, 123_274, 130_913])
    per_100 = recipients / subscribers * 100

    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.fill_between(years, per_100, 0, color=LIGHT_BLUE, alpha=0.7)
    ax.plot(years, per_100, color=NAVY, marker="o", markersize=7, linewidth=2.8)
    for year, value in zip(years, per_100):
        ax.annotate(
            f"{value:.1f}명",
            (year, value),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="bold",
            color=NAVY,
        )
    ax.set_ylim(0, 44)
    ax.set_xticks(years)
    ax.set_ylabel("가입자 100명당 전체 연금수급자(명)")
    ax.set_title("가입자 대비 전체 연금수급자 비율", loc="left", color=NAVY, pad=14)
    ax.text(
        0,
        1.02,
        "2021년 29.9명에서 2025년 39.4명으로 증가",
        transform=ax.transAxes,
        color=GRAY,
        fontsize=10,
    )
    style_axis(ax)
    add_source(
        fig,
        "사립학교교직원연금공단 홈페이지 ‘연도별 가입 현황’(2021~2025년 말)",
        "전체 연금수급자÷가입자×100, 팀 계산. 퇴직연금수급자만을 뜻하지 않음",
    )
    fig.subplots_adjust(bottom=0.17, top=0.82, right=0.94)
    save(fig, "06_가입자100명당_전체연금수급자.png")
    return {
        str(year): {
            "가입자": int(subscriber),
            "전체연금수급자": int(recipient),
            "가입자100명당수급자": round(float(ratio), 1),
        }
        for year, subscriber, recipient, ratio in zip(years, subscribers, recipients, per_100)
    }


def make_reason_figure() -> dict:
    rows = read_csv(find_csv("퇴직사유별 퇴직자 현황"))
    value_columns = [key for key in rows[0] if key not in {"기준년도", "지역", "퇴직사유"}]
    reason_totals: dict[str, int] = defaultdict(int)
    for row in rows:
        reason_totals[row["퇴직사유"]] += sum(integer(row[column]) for column in value_columns)

    primary = ["의원일반퇴직", "의원정년퇴직", "의원명예퇴직"]
    other = sum(value for reason, value in reason_totals.items() if reason not in primary)
    labels = ["의원일반퇴직", "의원정년퇴직", "의원명예퇴직", "기타"]
    values = [reason_totals[label] for label in primary] + [other]
    total = sum(values)
    percentages = [value / total * 100 for value in values]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    positions = np.arange(len(labels))
    colors = [NAVY, MID_BLUE, BLUE, PURPLE]
    bars = ax.barh(positions, values, color=colors, height=0.58)
    ax.invert_yaxis()
    ax.set_yticks(positions, labels)
    ax.set_xlabel("퇴직자 수(명)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_xlim(0, max(values) * 1.22)
    for bar, value, percentage in zip(bars, values, percentages):
        ax.text(
            value + max(values) * 0.018,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,}명  ({percentage:.1f}%)",
            va="center",
            fontsize=10,
            fontweight="bold" if value == max(values) else "normal",
            color=NAVY if value == max(values) else INK,
        )
    ax.set_title("2025년 교원 퇴직사유 구성", loc="left", color=NAVY, pad=14)
    ax.text(
        0,
        1.02,
        "학교급·지역·퇴직사유 파일 수록 14,193명 기준",
        transform=ax.transAxes,
        color=GRAY,
        fontsize=10,
    )
    style_axis(ax, grid_axis="x")
    add_source(
        fig,
        "공공데이터포털 ID 15131720(2025.12.31 기준)",
        "기타=사망·해임·당연·파면·의원. 연도별 퇴직현황 교원 총계 14,789명과 596명 차이",
    )
    fig.subplots_adjust(left=0.16, bottom=0.17, top=0.82, right=0.95)
    save(fig, "07_2025년_교원퇴직사유_구성.png")
    return {
        "원자료_퇴직사유별": dict(sorted(reason_totals.items(), key=lambda item: item[1], reverse=True)),
        "그래프_재분류": dict(zip(labels, values)),
        "파일내_총계": total,
        "연도별퇴직현황_교원총계": 14_789,
        "공식파일간_차이": 596,
    }


def semantic_age_band(label: str) -> str:
    if "이상" in label:
        return "90세 이상"
    found = re.search(r"\d+", label)
    if not found:
        raise ValueError(label)
    upper = int(found.group())
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


def make_age_figure() -> dict:
    rows = read_csv(find_csv("평균연금월액"))
    order = ["60세 미만", "60대", "70대", "80대", "90세 이상"]
    grouped = {band: {"교원": 0, "사무직원": 0} for band in order}
    for row in rows:
        band = semantic_age_band(row["연령"])
        grouped[band]["교원"] += integer(row["교원 남성수급자수(명)"]) + integer(row["교원 여성 수급자수(명)"])
        grouped[band]["사무직원"] += integer(row["사무직원 남성수급자수(명)"]) + integer(row["사무직원 여성 수급자수(명)"])

    teacher = np.array([grouped[band]["교원"] for band in order])
    staff = np.array([grouped[band]["사무직원"] for band in order])
    totals = teacher + staff
    grand_total = int(totals.sum())
    shares = totals / grand_total * 100
    sixty_plus_share = (grand_total - int(totals[0])) / grand_total * 100

    fig, ax = plt.subplots(figsize=(10, 5.7))
    positions = np.arange(len(order))
    width = 0.62
    ax.bar(positions, teacher, width=width, color=NAVY, label="교원")
    ax.bar(positions, staff, width=width, bottom=teacher, color=BLUE, label="사무직원")
    for position, total, share in zip(positions, totals, shares):
        ax.text(
            position,
            total + max(totals) * 0.025,
            f"{int(total):,}명\n({share:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color=NAVY,
        )
    ax.set_xticks(positions, order)
    ax.set_ylabel("퇴직연금수급자 수(명)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_ylim(0, max(totals) * 1.18)
    ax.legend(ncol=2, loc="upper right")
    ax.set_title("연령대별 퇴직연금수급자 분포", loc="left", color=NAVY, pad=14)
    ax.text(
        0,
        1.02,
        f"2026년 6월 기준 총 {grand_total:,}명 · 60세 이상 {sixty_plus_share:.1f}%",
        transform=ax.transAxes,
        color=GRAY,
        fontsize=10,
    )
    style_axis(ax)
    add_source(
        fig,
        "공공데이터포털 ID 15045812(2026.06.24 기준)",
        "원자료 ‘n미만’을 상한 미만으로 해석해 60미만 행을 60세 미만에 포함; 남녀 합산",
    )
    fig.subplots_adjust(bottom=0.18, top=0.82, right=0.96)
    save(fig, "08_연령대별_퇴직연금수급자_분포.png")
    return {
        "구간정의": "원자료 ‘n미만’을 상한 미만으로 해석하고 60미만 행을 60세 미만에 포함",
        "연령대별": {
            band: {
                **grouped[band],
                "합계": int(totals[index]),
                "비중_pct": round(float(shares[index]), 1),
            }
            for index, band in enumerate(order)
        },
        "총계": grand_total,
        "60세이상_비중_pct": round(float(sixty_plus_share), 1),
    }


def main() -> None:
    configure_plotting()
    payload = {
        "검증일": "2026-08-31",
        "06_가입자100명당_전체연금수급자": make_ratio_figure(),
        "07_2025년_교원퇴직사유_구성": make_reason_figure(),
        "08_연령대별_퇴직연금수급자_분포": make_age_figure(),
    }
    assert payload["07_2025년_교원퇴직사유_구성"]["파일내_총계"] == 14_193
    assert payload["08_연령대별_퇴직연금수급자_분포"]["총계"] == 118_656
    EVIDENCE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for path in sorted(FIGURES.glob("*.png")):
        print(path)
    print(EVIDENCE)


if __name__ == "__main__":
    main()
