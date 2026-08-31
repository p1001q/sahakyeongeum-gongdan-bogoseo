#!/usr/bin/env python3
"""활성 문서·데이터·코드·그림의 접근성과 기본 무결성을 점검한다."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_MARKDOWN = [
    ROOT / "AGENTS.md",
    ROOT / "START_HERE.md",
    ROOT / "USER_CONTEXT.md",
    ROOT / "PROJECT_CONTEXT.md",
    ROOT / "docs/00_문서_인덱스_및_현재_기준.md",
    ROOT / "docs/01_추진계획안_전문분석.md",
    ROOT / "docs/04_프로젝트_목표_및_기대효과_해설.md",
    ROOT / "docs/10_강석_담당자_회신_및_프로젝트_방향_2026-08-29.md",
    ROOT / "docs/13_공단_제출보고서_사고흐름_및_양식가이드_2026-08-30.md",
    ROOT / "docs/15_사학연금공단_공공데이터_186개_전수검토_2026-08-31.md",
    ROOT / "docs/16_최종_보고서_목차_및_논리구조_픽스_2026-08-31.md",
    ROOT / "docs/17_팀원_그래프_7종_검증_및_활용판정_2026-08-31.md",
    ROOT / "docs/18_보고서_장별패키지_제작_인수인계_2026-08-31.md",
    ROOT / "docs/19_새_세션_장별패키지_제작_프롬프트_2026-08-31.md",
    ROOT / "output/figures/team_candidates/README.md",
    ROOT / "output/figures/verified/README.md",
    ROOT / "output/report_packages/README.md",
    ROOT / "archive/README.md",
]
ACTIVE_SCRIPTS = [
    ROOT / "scripts/analyze_public_data.py",
    ROOT / "scripts/audit_tp_catalog.py",
    ROOT / "scripts/analyze_catalog_audit.py",
    ROOT / "scripts/verify_team_graphs.py",
    ROOT / "scripts/create_verified_supplementary_figures.py",
    ROOT / "scripts/verify_workspace.py",
]
REQUIRED = ACTIVE_MARKDOWN + ACTIVE_SCRIPTS + [
    ROOT / "추진계획안.pdf",
    ROOT / "data/raw/사립학교교직원연금공단_연도별_교직원_퇴직현황_20251231.csv",
    ROOT / "data/raw/사립학교교직원연금공단_연도별_연금수급자_및_연금액_20251231.csv",
    ROOT / "data/catalog/사학연금공단_공공데이터_186개_목록_20260831.csv",
    ROOT / "data/catalog/핵심후보_원본파일_무결성_20260831.csv",
]
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CODE_PATTERN = re.compile(r"`([^`\n]+)`")
ROOT_PREFIXES = {"archive", "assets", "data", "docs", "output", "scripts"}
INTENTIONALLY_ABSENT = {
    "tmp/",
    "output/qa/",
    "output/report_packages/03_퇴직자·수급자_변화분석_패키지.md",
    "output/report_packages/04_현행_디지털고객서비스_분석_패키지.md",
    "output/report_packages/05_분석공백_및_품질진단_패키지.md",
    "output/report_packages/06_공공데이터_고도화방안_패키지.md",
    "output/report_packages/07_공단활용_로드맵_KPI_패키지.md",
    "output/report_packages/01_연구개요_패키지.md",
    "output/report_packages/02_공공데이터_활용및검증방법_패키지.md",
    "output/report_packages/08_결론_패키지.md",
    "output/report_packages/00_요약문_패키지.md",
    "output/report_packages/99_전문보고서AI_통합전달본.md",
}


def read_csv(path: Path) -> tuple[int, int, str]:
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            with path.open(encoding=encoding, newline="") as handle:
                rows = list(csv.reader(handle))
            return max(len(rows) - 1, 0), len(rows[0]) if rows else 0, encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"지원 인코딩으로 읽을 수 없음: {path}")


def main() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
    all_markdown = sorted(ROOT.rglob("*.md"))
    markdown_errors = []
    for path in all_markdown:
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            markdown_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    broken_links: list[dict[str, str]] = []
    broken_code_paths: list[dict[str, str]] = []
    for md in ACTIVE_MARKDOWN:
        if not md.exists():
            continue
        text = md.read_text(encoding="utf-8")
        for target in LINK_PATTERN.findall(text):
            target = target.strip().strip("<>").split("#", 1)[0]
            if not target or re.match(r"^(?:https?|mailto|notion):", target):
                continue
            resolved = (md.parent / target).resolve()
            if not resolved.exists():
                broken_links.append(
                    {"문서": str(md.relative_to(ROOT)), "대상": target}
                )
        for target in CODE_PATTERN.findall(text):
            target = target.strip().rstrip(".,;:")
            if not target or "*" in target or re.match(r"^(?:https?|notion):", target):
                continue
            if target in INTENTIONALLY_ABSENT or target.startswith(("python ", "python3 ", "bash ", "zsh ")):
                continue
            looks_like_path = "/" in target or Path(target).suffix in {".md", ".pdf", ".csv", ".json", ".py", ".png", ".docx"}
            if not looks_like_path:
                continue
            if target.startswith(("../", "./")):
                resolved = (md.parent / target).resolve()
            elif target.split("/", 1)[0] in ROOT_PREFIXES or target in {"AGENTS.md", "START_HERE.md", "USER_CONTEXT.md", "PROJECT_CONTEXT.md", "추진계획안.pdf"}:
                resolved = (ROOT / target).resolve()
            else:
                resolved = (md.parent / target).resolve()
            # `docs/16`처럼 설명 편의를 위한 확장자 없는 별칭은 경로 검사에서 제외한다.
            if not Path(target).suffix and not target.endswith("/") and not resolved.exists():
                continue
            if not resolved.exists():
                broken_code_paths.append(
                    {"문서": str(md.relative_to(ROOT)), "대상": target}
                )

    csv_results = {}
    for path in sorted((ROOT / "data").rglob("*.csv")):
        rows, columns, encoding = read_csv(path)
        csv_results[str(path.relative_to(ROOT))] = {
            "행수": rows,
            "열수": columns,
            "인코딩": encoding,
        }

    json_results = {}
    json_paths = list((ROOT / "data").rglob("*.json"))
    json_paths.extend((ROOT / "output/evidence").rglob("*.json"))
    for path in sorted(json_paths):
        json.loads(path.read_text(encoding="utf-8"))
        json_results[str(path.relative_to(ROOT))] = "정상"

    bad_png = []
    png_paths = sorted((ROOT / "output/figures").rglob("*.png"))
    for path in png_paths:
        if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            bad_png.append(str(path.relative_to(ROOT)))

    syntax_errors = []
    for path in ACTIVE_SCRIPTS:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            syntax_errors.append(f"{path.relative_to(ROOT)}:{exc.lineno} {exc.msg}")

    pdf_errors = []
    for path in sorted(ROOT.rglob("*.pdf")):
        if not path.read_bytes().startswith(b"%PDF-"):
            pdf_errors.append(str(path.relative_to(ROOT)))

    docx_errors = []
    for path in sorted(ROOT.rglob("*.docx")):
        try:
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
            if bad_member:
                docx_errors.append(f"{path.relative_to(ROOT)}: {bad_member}")
        except zipfile.BadZipFile:
            docx_errors.append(f"{path.relative_to(ROOT)}: ZIP 구조 오류")

    report = {
        "점검일": "2026-08-31",
        "판정": "정상" if not (missing or markdown_errors or broken_links or broken_code_paths or bad_png or syntax_errors or pdf_errors or docx_errors) else "확인필요",
        "필수파일_누락": missing,
        "Markdown_개수": len(all_markdown),
        "Markdown_UTF8오류": markdown_errors,
        "활성MD_로컬링크오류": broken_links,
        "활성MD_코드경로오류": broken_code_paths,
        "CSV_읽기검사": csv_results,
        "JSON_읽기검사": json_results,
        "PNG_개수": len(png_paths),
        "PNG_오류": bad_png,
        "Python_구문오류": syntax_errors,
        "PDF_오류": pdf_errors,
        "DOCX_오류": docx_errors,
        "보호경로": {
            "원본": ["추진계획안.pdf", "data/raw/"],
            "과거자료": ["archive/legacy_report_20260831/", "archive/forms_application_20260827/"],
        },
    }
    destination = ROOT / "data/catalog/워크스페이스_무결성점검_20260831.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["판정"] != "정상":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
