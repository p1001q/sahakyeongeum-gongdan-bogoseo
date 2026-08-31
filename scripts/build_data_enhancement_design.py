#!/usr/bin/env python3
"""Ⅵ장 공공데이터 고도화 제안의 정의서·코드표·우선순위·그림을 생성한다.

이 스크립트는 실제 관측값이나 가상 관측값을 만들지 않는다. 제안 데이터의
필드·코드·산식·보호규칙과 보고서용 개념 그림만 구조화한다.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
EVIDENCE = ROOT / "output" / "evidence"
FIGURES = ROOT / "output" / "figures" / "verified"

TASK_CACHE = Path(tempfile.gettempdir()) / "tp-enhancement-design-cache"
TASK_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TASK_CACHE / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(TASK_CACHE / "xdg"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


NAVY = "#24364B"
BLUE = "#138ACB"
MID_BLUE = "#4C78A8"
PURPLE = "#7A6FA6"
CORAL = "#D66A5E"
GREEN = "#4C956C"
GRAY = "#68737D"
LIGHT_BLUE = "#D9EDF7"
LIGHT_GRAY = "#EEF1F4"
LIGHT_PURPLE = "#E7E4ED"
INK = "#222222"


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
            "text.color": INK,
            "figure.dpi": 150,
            "savefig.dpi": 240,
        }
    )


def field_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(dataset: str, order: int, field: str, label: str, role: str, dtype: str, rule: str, required: str, phase: str, basis: str, privacy: str) -> None:
        rows.append(
            {
                "제안데이터명": dataset,
                "필드순서": order,
                "필드명": field,
                "한글명": label,
                "역할": role,
                "자료형": dtype,
                "형식_코드규칙": rule,
                "필수여부": required,
                "도입단계": phase,
                "제안근거": basis,
                "보호_품질주의": privacy,
            }
        )

    auth = "연령대·채널·인증방법별 홈페이지 인증현황"
    add(auth, 1, "base_ym", "기준연월", "차원", "문자열", "YYYY-MM", "필수", "2단계", "월별 변화·현행화", "일 단위보다 월 단위 우선")
    add(auth, 2, "user_group", "이용자구분", "차원", "범주", "재직자|수급자|기타·미분류", "필수", "2단계", "집단별 이용 차이", "개인 신분·기관명 공개 금지")
    add(auth, 3, "age_band", "연령대", "차원", "범주", "40세미만|40대|50대|60대|70대|80세이상|미상", "필수", "2단계", "담당자 연령별 제안", "정확한 나이·생년월일 금지; 희소범주 통합")
    add(auth, 4, "access_channel", "접속채널", "차원", "범주", "PC웹|모바일웹|앱|기타·미상", "필수", "2단계", "담당자 PC/모바일 제안", "기기ID·IP·브라우저 지문 금지")
    add(auth, 5, "auth_method", "인증방법", "차원", "범주", "간편인증|금융인증서|공동인증서|ID·비밀번호|기타·미상|해당없음", "필수", "2단계", "담당자 인증방법 제안", "인증서 식별값·계정ID 금지")
    add(auth, 6, "access_count", "접속건수", "측정값", "정수", "0 이상", "필수", "2단계", "PC/모바일 접속 규모", "공개 셀은 억제규칙 적용")
    add(auth, 7, "auth_attempt_count", "인증시도건수", "측정값", "정수", "0 이상", "필수", "2단계", "인증 퍼널 분모", "중복시도 정의 명시")
    add(auth, 8, "auth_success_count", "인증성공건수", "측정값", "정수", "0 이상", "필수", "2단계", "인증성공률", "성공+실패와 시도 합계 검증")
    add(auth, 9, "auth_failure_count", "인증실패건수", "측정값", "정수", "0 이상", "필수", "2단계", "담당자 인증실패 제안", "성공+실패와 시도 합계 검증")
    add(auth, 10, "password_reset_count", "비밀번호재설정건수", "측정값", "정수", "0 이상", "필수", "2단계", "비밀번호 분실 지원", "ID·비밀번호 인증에만 적용 여부 명시")
    add(auth, 11, "alimtalk_target_count", "인증알림톡대상건수", "측정값", "정수", "0 이상", "권장", "2단계", "발송률 분모", "전화번호·메시지 내용 공개 금지")
    add(auth, 12, "alimtalk_sent_count", "인증알림톡발송건수", "측정값", "정수", "0 이상", "필수", "2단계", "담당자 알림톡 발송 제안", "전화번호·메시지 내용 공개 금지")
    add(auth, 13, "suppression_status", "소수셀처리상태", "품질", "범주", "공개|억제|상위범주통합", "필수", "2단계", "재식별 위험 관리", "기준 미만 셀·보완억제 표시")
    add(auth, 14, "aggregation_version", "집계기준버전", "품질", "문자열", "예: v1.0 형식", "필수", "2단계", "산식 변경 추적", "버전별 수정이력 연결")

    service = "연령대·채널·서비스유형별 디지털 업무처리현황"
    add(service, 1, "base_ym", "기준연월", "차원", "문자열", "YYYY-MM", "필수", "3단계", "월별 처리흐름", "월 단위 공개")
    add(service, 2, "user_group", "이용자구분", "차원", "범주", "재직자|수급자|기타·미분류", "필수", "3단계", "집단별 완료 차이", "개인·기관 식별값 금지")
    add(service, 3, "age_band", "연령대", "차원", "범주", "40세미만|40대|50대|60대|70대|80세이상|미상", "필수", "3단계", "연령대별 완료 분석", "희소범주 통합")
    add(service, 4, "access_channel", "접속채널", "차원", "범주", "PC웹|모바일웹|앱|기타·미상", "필수", "3단계", "채널별 완료 분석", "기기식별값 금지")
    add(service, 5, "service_type", "서비스유형", "차원", "범주", "공단 현행 업무코드의 공개용 상위범주; 기존 인터넷 접수 7종과 매핑", "필수", "3단계", "업무별 완료·이탈", "희소서비스 상위범주 통합")
    add(service, 6, "task_start_count", "업무시작건수", "측정값", "정수", "0 이상", "필수", "3단계", "완료·이탈률 분모", "업무시작 이벤트 정의 명시")
    add(service, 7, "task_complete_count", "업무완료건수", "측정값", "정수", "0 이상", "필수", "3단계", "업무완료율", "완료+이탈+기타 종료 검증")
    add(service, 8, "task_abandon_count", "중도이탈건수", "측정값", "정수", "0 이상", "필수", "3단계", "중도이탈률", "타임아웃 기준 명시")
    add(service, 9, "consult_transfer_count", "상담전환건수", "측정값", "정수", "0 이상", "필수", "3단계", "디지털→상담 전환율", "내부 집계키만 사용; 공개키 금지")
    add(service, 10, "repeat_consult_count", "반복상담건수", "측정값", "정수", "0 이상", "권장", "3단계", "반복문의 관리", "반복 기준기간 명시; 공개키 금지")
    add(service, 11, "suppression_status", "소수셀처리상태", "품질", "범주", "공개|억제|상위범주통합", "필수", "3단계", "재식별 위험 관리", "기준 미만 셀·보완억제 표시")
    add(service, 12, "aggregation_version", "집계기준버전", "품질", "문자열", "예: v1.0 형식", "필수", "3단계", "산식 변경 추적", "수정이력 연결")

    failure = "연령대·채널·인증방법별 인증실패사유 현황"
    add(failure, 1, "base_ym", "기준연월", "차원", "문자열", "YYYY-MM", "필수", "3단계", "실패사유 월별 변화", "월 단위 공개")
    add(failure, 2, "user_group", "이용자구분", "차원", "범주", "재직자|수급자|기타·미분류", "필수", "3단계", "집단별 실패사유", "개인식별값 금지")
    add(failure, 3, "age_band", "연령대", "차원", "범주", "40세미만|40대|50대|60대|70대|80세이상|미상", "필수", "3단계", "연령대별 실패사유", "희소범주 통합")
    add(failure, 4, "access_channel", "접속채널", "차원", "범주", "PC웹|모바일웹|앱|기타·미상", "필수", "3단계", "채널별 실패사유", "기기식별값 금지")
    add(failure, 5, "auth_method", "인증방법", "차원", "범주", "간편인증|금융인증서|공동인증서|ID·비밀번호|기타·미상", "필수", "3단계", "방법별 실패사유", "인증서 식별값 금지")
    add(failure, 6, "failure_reason", "실패사유범주", "차원", "범주", "자격정보불일치|비밀번호불일치|사용자취소|시간초과|시스템·통신오류|기타·미상", "필수", "3단계", "개선대상 식별", "원문 오류메시지·자유서술 공개 금지")
    add(failure, 7, "auth_failure_count", "인증실패건수", "측정값", "정수", "0 이상", "필수", "3단계", "실패사유 비중", "인증현황 파일 실패합과 교차검증")
    add(failure, 8, "suppression_status", "소수셀처리상태", "품질", "범주", "공개|억제|상위범주통합", "필수", "3단계", "재식별 위험 관리", "기준 미만 셀·보완억제 표시")
    add(failure, 9, "aggregation_version", "집계기준버전", "품질", "문자열", "예: v1.0 형식", "필수", "3단계", "산식 변경 추적", "수정이력 연결")
    return rows


def code_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def extend(field: str, values: list[tuple[str, str]], note: str) -> None:
        for order, (code, label) in enumerate(values, 1):
            rows.append({"필드명": field, "코드순서": order, "코드값": code, "표시명": label, "정의_주의": note})

    extend("user_group", [("EMP", "재직자"), ("PEN", "수급자"), ("OTH", "기타·미분류")], "현행 공단 고객구분과 매핑 후 확정")
    extend("age_band", [("U40", "40세 미만"), ("A40", "40대"), ("A50", "50대"), ("A60", "60대"), ("A70", "70대"), ("A80P", "80세 이상"), ("UNK", "미상")], "정확한 나이·생년월일을 공개하지 않으며 희소셀은 인접 범주와 통합")
    extend("access_channel", [("PCW", "PC웹"), ("MOW", "모바일웹"), ("APP", "앱"), ("OTH", "기타·미상")], "담당자 PC/모바일 항목을 포함하고 앱을 분리")
    extend("auth_method", [("SIMPLE", "간편인증"), ("FINCERT", "금융인증서"), ("JOINT", "공동인증서"), ("IDPW", "ID·비밀번호"), ("OTHER", "기타·미상"), ("NA", "해당없음")], "공단 현행 인증수단과 대조 후 코드 확정")
    extend("failure_reason", [("MISMATCH", "자격정보불일치"), ("PASSWORD", "비밀번호불일치"), ("CANCEL", "사용자취소"), ("TIMEOUT", "시간초과"), ("SYSTEM", "시스템·통신오류"), ("OTHER", "기타·미상")], "자유서술·원문 오류메시지 대신 공개용 범주 사용")
    extend("suppression_status", [("OPEN", "공개"), ("SUPP", "억제"), ("MERGED", "상위범주통합")], "공단 재식별 위험검토에서 최소셀 기준 k를 확정")
    return rows


def quality_rows() -> list[dict[str, str]]:
    return [
        {"요건ID": "E1", "개선영역": "정의", "Ⅴ장근거": "수급자 111,389·114,079·118,656명", "필수개선항목": "기준일·모집단·포함범위·산식·공식 기준통계", "검사규칙": "5개 메타데이터 항목 공란 없음", "품질KPI": "핵심지표 정의완결률", "단계": "1단계"},
        {"요건ID": "E2", "개선영역": "합계", "Ⅴ장근거": "상담 채널 합계 차이", "필수개선항목": "총계·부문합 자동검증과 미분류·조정항목", "검사규칙": "총계=부문합 또는 차이사유 코드 존재", "품질KPI": "부문합계 일치율·절대불일치율", "단계": "1단계"},
        {"요건ID": "E3", "개선영역": "날짜", "Ⅴ장근거": "2025-MM-YY 연월 표기", "필수개선항목": "YYYY-MM 표준·기준시점·집계기간", "검사규칙": "정규식과 날짜 유효성 검사 통과", "품질KPI": "표준연월 준수율", "단계": "1단계"},
        {"요건ID": "E4", "개선영역": "컬럼·단위", "Ⅴ장근거": "75세 건수열·평균연금월액", "필수개선항목": "헤더·단위·자료형·산식 동시 정정", "검사규칙": "헤더 의미와 값범위·단위 검증", "품질KPI": "컬럼정의·단위메타데이터 일치율", "단계": "1단계"},
        {"요건ID": "E5", "개선영역": "코드", "Ⅴ장근거": "인터넷 접수 미구분", "필수개선항목": "미상·미분류 코드와 분류기준", "검사규칙": "코드표 밖 값 없음·미분류 비중 산출", "품질KPI": "미분류 비중", "단계": "1단계"},
        {"요건ID": "E6", "개선영역": "수정이력", "Ⅴ장근거": "값 차이 원인·정정이력 부족", "필수개선항목": "변경일·변경필드·전후값·사유·버전", "검사규칙": "수정 파일의 이력 레코드 존재", "품질KPI": "정정이력 공개율", "단계": "1단계"},
        {"요건ID": "E7", "개선영역": "현행화", "Ⅴ장근거": "2020년 8월 수급종료자 단면", "필수개선항목": "통계기준일과 갱신주기 분리 표기", "검사규칙": "예정 주기 내 갱신 또는 1회성 표시", "품질KPI": "현행화 준수율·갱신지연일수", "단계": "1단계"},
        {"요건ID": "E8", "개선영역": "교차연계", "Ⅴ장근거": "유사지표 파일 간 사용기준 부족", "필수개선항목": "동일·유사지표 매핑과 권장 사용처", "검사규칙": "교차자료 쌍마다 차이설명 또는 기준통계", "품질KPI": "교차자료 총계 설명률", "단계": "1단계"},
    ]


def priority_rows() -> list[dict[str, str]]:
    return [
        {"단계": "1단계", "목표": "기존 파일 신뢰기반 정비", "핵심항목": "정의·합계·YYYY-MM·컬럼·단위·수정이력·갱신주기", "주요산출물": "정정 파일·데이터사전·품질검사표", "선행조건": "Ⅴ장 8개 사례 담당 검토", "보호조치": "개인정보 추가 수집 없음", "완료판정": "자동검사 통과와 변경이력 공개"},
        {"단계": "2단계", "목표": "담당자 제안 4개 통계 시범 개방", "핵심항목": "연령대×PC/모바일×인증방법×인증성공·실패×비밀번호 재설정·알림톡", "주요산출물": "인증현황 월별 집계·코드표", "선행조건": "로그 정의·분모·중복시도 기준 확정", "보호조치": "월·연령대 집계, 소수셀 억제, 식별자 미공개", "완료판정": "필드·합계·억제 QA 통과"},
        {"단계": "3단계", "목표": "서비스 완료와 채널 전환 연결", "핵심항목": "서비스유형·실패사유·업무완료·중도이탈·상담전환·반복상담", "주요산출물": "업무처리현황·실패사유 월별 집계", "선행조건": "내부 이벤트·상담의 일회성 집계키 설계", "보호조치": "집계 후 내부키 폐기, 희소서비스 통합, 보완억제", "완료판정": "전환 산식 재현·재식별위험 검토 통과"},
        {"단계": "4단계", "목표": "정기 공개와 활용 환류", "핵심항목": "정기 갱신·외부 활용사례·오류신고·재개방", "주요산출물": "정기 공개파일·수정이력·활용성과 기록", "선행조건": "담당 조직·갱신주기·검수책임 확정", "보호조치": "정기 재식별 위험검토와 코드·억제기준 재평가", "완료판정": "갱신준수·활용사례·품질개선 환류 기록"},
    ]


def kpi_rows() -> list[dict[str, str]]:
    return [
        {"KPI": "인증성공률", "산식": "인증성공건수÷인증시도건수×100", "필요데이터": "인증현황", "현재산출": "불가", "주의": "시도 중복·해당없음 기준 명시"},
        {"KPI": "인증실패율", "산식": "인증실패건수÷인증시도건수×100", "필요데이터": "인증현황", "현재산출": "불가", "주의": "성공+실패와 시도 합계 검증"},
        {"KPI": "업무완료율", "산식": "업무완료건수÷업무시작건수×100", "필요데이터": "업무처리현황", "현재산출": "불가", "주의": "완료 정의와 보완요청 처리 명시"},
        {"KPI": "중도이탈률", "산식": "중도이탈건수÷업무시작건수×100", "필요데이터": "업무처리현황", "현재산출": "불가", "주의": "타임아웃·사용자종료 기준 명시"},
        {"KPI": "디지털→상담 전환율", "산식": "상담전환건수÷업무시작건수×100", "필요데이터": "업무처리현황", "현재산출": "불가", "주의": "전환 인정기간과 최초·최종채널 명시"},
        {"KPI": "반복상담률", "산식": "반복상담건수÷상담전환건수×100", "필요데이터": "업무처리현황", "현재산출": "불가", "주의": "동일 문제·반복기간 정의"},
        {"KPI": "비밀번호재설정률", "산식": "비밀번호재설정건수÷ID·비밀번호 인증시도건수×100", "필요데이터": "인증현황", "현재산출": "불가", "주의": "ID·비밀번호 방식에 한정"},
        {"KPI": "인증알림톡 발송률", "산식": "인증알림톡발송건수÷인증알림톡대상건수×100", "필요데이터": "인증현황", "현재산출": "불가", "주의": "발송 성공·실패 정의와 개인정보 미공개"},
    ]


def draw_box(ax: plt.Axes, x: float, y: float, w: float, h: float, title: str, lines: list[str], face: str, edge: str = NAVY) -> None:
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.3, edgecolor=edge, facecolor=face)
    ax.add_patch(patch)
    ax.text(x + w/2, y + h - 0.045, title, ha="center", va="top", fontsize=11, fontweight="bold", color=NAVY)
    ax.text(x + 0.025, y + h - 0.10, "\n".join(lines), ha="left", va="top", fontsize=8.7, color=INK, linespacing=1.45)


def make_connection_figure() -> None:
    fig, ax = plt.subplots(figsize=(12, 7.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.02, 0.96, "현재 공개데이터에서 제안 연결통계로의 고도화 모형", fontsize=17, fontweight="bold", color=NAVY, va="top")
    ax.text(0.02, 0.91, "개별 현황자료를 보존하면서 품질축과 연결통계축을 병행", fontsize=10, color=GRAY, va="top")

    draw_box(ax, 0.03, 0.17, 0.23, 0.64, "현재 공개자료", ["홈페이지 가입자", "고객 상담 채널", "업무구분별 VOC", "인터넷 접수 7종", "게시물 활용", "퇴직자·수급자 현황", "", "자료별 현황은 확인", "공통 연결키는 없음"], LIGHT_GRAY)
    draw_box(ax, 0.36, 0.56, 0.27, 0.25, "1축  기존 파일 품질개선", ["기준일·모집단·산식", "총계 자동검증", "YYYY-MM·컬럼·단위", "수정이력·갱신주기"], LIGHT_PURPLE, PURPLE)
    draw_box(ax, 0.36, 0.17, 0.27, 0.30, "2축  신규 비식별 연결통계", ["월×이용자구분×연령대", "PC웹·모바일웹·앱", "인증방법·성공·실패", "서비스 시작·완료·이탈", "상담 전환·반복상담"], LIGHT_BLUE, BLUE)
    draw_box(ax, 0.73, 0.17, 0.24, 0.64, "산출 가능한 판단", ["인증성공·실패율", "업무완료·이탈률", "디지털→상담 전환율", "반복상담률", "비밀번호 재설정률", "", "공단 서비스 개선", "외부 연구·활용", "품질개선 후 재개방"], "#E8F3EC", GREEN)

    for y in (0.685, 0.32):
        ax.add_patch(FancyArrowPatch((0.27, y), (0.35, y), arrowstyle="-|>", mutation_scale=18, linewidth=1.5, color=GRAY))
    ax.add_patch(FancyArrowPatch((0.64, 0.685), (0.72, 0.685), arrowstyle="-|>", mutation_scale=18, linewidth=1.5, color=GRAY))
    ax.add_patch(FancyArrowPatch((0.64, 0.32), (0.72, 0.32), arrowstyle="-|>", mutation_scale=18, linewidth=1.5, color=GRAY))
    ax.text(0.315, 0.84, "정비", ha="center", color=GRAY, fontsize=9)
    ax.text(0.315, 0.46, "연결", ha="center", color=GRAY, fontsize=9)
    ax.text(0.68, 0.84, "신뢰", ha="center", color=GRAY, fontsize=9)
    ax.text(0.68, 0.46, "분석", ha="center", color=GRAY, fontsize=9)
    fig.text(0.02, 0.025, "제안: 상상이상 팀  |  근거: 공단 공식 공개데이터 분석·품질진단 및 강석 담당자 회신(2026.08.29)", fontsize=7.6, color=GRAY)
    fig.savefig(FIGURES / "15_현재데이터_제안연결통계_고도화모형.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_priority_figure() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.02, 0.95, "단계별 공공데이터 고도화 우선순위", fontsize=17, fontweight="bold", color=NAVY, va="top")
    ax.text(0.02, 0.89, "기존 파일을 먼저 정비하고 핵심 통계를 시범 개방한 뒤 연결범위를 확장", fontsize=10, color=GRAY, va="top")
    stages = [
        (0.03, "1단계", "기존 파일 품질정비", ["정의·합계", "날짜·단위", "수정이력"], PURPLE, LIGHT_PURPLE),
        (0.275, "2단계", "담당자 4개 통계", ["PC/모바일", "인증방법·실패", "비밀번호 알림톡"], BLUE, LIGHT_BLUE),
        (0.52, "3단계", "완료·전환 연결", ["서비스유형", "완료·중도이탈", "상담전환·반복"], CORAL, "#F7E8E5"),
        (0.765, "4단계", "정기 공개·환류", ["정기 갱신", "외부 활용", "품질개선·재개방"], GREEN, "#E8F3EC"),
    ]
    for x, stage, title, lines, edge, face in stages:
        draw_box(ax, x, 0.24, 0.205, 0.50, f"{stage}  {title}", lines, face, edge)
        ax.text(x+0.1025, 0.18, "→ 다음 단계 QA 통과 후 확장" if stage != "4단계" else "→ 활용성과를 다시 데이터에 반영", ha="center", fontsize=8, color=GRAY)
    for x in (0.245, 0.49, 0.735):
        ax.add_patch(FancyArrowPatch((x, 0.49), (x+0.025, 0.49), arrowstyle="-|>", mutation_scale=17, linewidth=1.4, color=GRAY))
    fig.text(0.02, 0.025, "주: 일정·목표값은 기준선과 공단 운영여건 확인 후 Ⅶ장에서 확정하며, 본 그림은 실행 순서 제안임", fontsize=7.7, color=GRAY)
    fig.savefig(FIGURES / "16_공공데이터_고도화_4단계_우선순위.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    configure_plotting()

    fields = pd.DataFrame(field_rows())
    codes = pd.DataFrame(code_rows())
    quality = pd.DataFrame(quality_rows())
    priority = pd.DataFrame(priority_rows())
    kpis = pd.DataFrame(kpi_rows())
    fields.to_csv(PROCESSED / "신규개방_디지털서비스_데이터정의서.csv", index=False, encoding="utf-8-sig")
    codes.to_csv(PROCESSED / "신규개방_디지털서비스_코드값정의.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(PROCESSED / "기존공개데이터_품질개선_요건.csv", index=False, encoding="utf-8-sig")
    priority.to_csv(PROCESSED / "공공데이터_고도화_단계별우선순위.csv", index=False, encoding="utf-8-sig")
    kpis.to_csv(PROCESSED / "신규개방_서비스KPI_산식.csv", index=False, encoding="utf-8-sig")

    required_checks = {
        "PC_모바일": fields["형식_코드규칙"].str.contains("PC웹.*모바일웹", regex=True).any(),
        "인증방법": fields["필드명"].eq("auth_method").any(),
        "인증실패": fields["필드명"].eq("auth_failure_count").any(),
        "비밀번호_알림톡": fields["필드명"].eq("alimtalk_sent_count").any(),
        "업무완료_중도이탈": fields["필드명"].isin(["task_complete_count", "task_abandon_count"]).sum() == 2,
        "상담전환_반복상담": fields["필드명"].isin(["consult_transfer_count", "repeat_consult_count"]).sum() == 2,
        "식별자_공개필드없음": not fields["필드명"].str.contains("user_id|ip|device_id|birth", regex=True).any(),
        "소수셀처리상태": fields["필드명"].eq("suppression_status").sum() == 3,
    }
    assert all(required_checks.values())

    evidence = {
        "작성일": "2026-08-31",
        "성격": "실제값이 아닌 공공데이터 신규개방 설계안",
        "제안데이터셋수": int(fields["제안데이터명"].nunique()),
        "제안필드수": int(len(fields)),
        "코드값정의수": int(len(codes)),
        "기존품질개선요건수": int(len(quality)),
        "단계수": int(len(priority)),
        "서비스KPI수": int(len(kpis)),
        "담당자제안_필수반영검사": {key: bool(value) for key, value in required_checks.items()},
        "공개행단위": {
            name: " × ".join(fields[(fields["제안데이터명"] == name) & (fields["역할"] == "차원")]["한글명"].tolist())
            for name in fields["제안데이터명"].drop_duplicates()
        },
        "보호원칙": [
            "개인별 행이 아닌 월별 범주 집계만 공개",
            "정확한 나이·생년월일·기관명·사용자ID·IP·기기ID·전화번호·오류원문은 공개하지 않음",
            "공단 재식별위험 검토에서 최소셀 기준 k를 확정하고 k 미만 셀은 억제 또는 상위범주 통합",
            "주변 합계로 억제값을 역산할 수 있으면 보완억제 적용",
            "전환·반복 분석용 내부 일회성 집계키는 공개하지 않고 집계 후 폐기",
            "공개 전 합계·코드·기간·억제·버전 QA를 통과",
        ],
    }
    (EVIDENCE / "Ⅵ_공공데이터_고도화설계_검증_20260831.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    make_connection_figure()
    make_priority_figure()
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
