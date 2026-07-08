"""BOHUMFIT-193 신규 가입제안서 담보 매핑 레지스트리."""
from __future__ import annotations

from dataclasses import dataclass

from .constants import AGG_REP, AGG_SUM

REGISTRY_VERSION = "BOHUMFIT-193-S4"
DEFAULT_PAY_MONTHS = 240


@dataclass(frozen=True)
class ProposalRule:
    kb_name: str
    group12: str
    agg: str
    keywords: tuple[str, ...]
    excludes: tuple[str, ...] = ()
    merge_rule: str = AGG_REP


@dataclass(frozen=True)
class RegistryCoverage:
    kb_name: str
    amount: int
    group12: str
    agg: str
    note: str
    merge_rule: str = AGG_REP
    include_in_coverages: bool = True


@dataclass(frozen=True)
class ProductProfile:
    key: str
    insurer: str
    product: str
    keywords: tuple[str, ...]
    fallback_premium: int
    fallback_coverages: tuple[RegistryCoverage, ...] = ()
    bundle_coverages: tuple[RegistryCoverage, ...] = ()


PROPOSAL_RULES: tuple[ProposalRule, ...] = (
    ProposalRule("상해사망", "사망", AGG_SUM, ("일반상해사망",)),
    ProposalRule("상해사망", "사망", AGG_SUM, ("재해사망보험금",)),
    ProposalRule("상해80%미만후유장해", "후유장해", AGG_SUM, ("일반상해후유장해",)),
    ProposalRule("상해80%미만후유장해", "후유장해", AGG_SUM, ("상해후유장해",)),
    ProposalRule("일반암", "암", AGG_SUM, ("암진단비", "유사암제외"), excludes=("통합치료비", "납입면제")),
    ProposalRule("일반암", "암", AGG_SUM, ("암(유사암제외)진단특약",)),
    ProposalRule("유사암", "암", AGG_SUM, ("유사암", "진단"), excludes=("유사암제외",)),
    ProposalRule("뇌혈관질환", "뇌", AGG_SUM, ("뇌혈관질환", "진단"), excludes=("수술",)),
    ProposalRule("허혈성심장질환", "심장", AGG_SUM, ("허혈성심장질환", "진단"), excludes=("수술",)),
    ProposalRule("급성심근경색증", "심장", AGG_SUM, ("심장질환", "특정Ⅱ")),
    ProposalRule("심장질환(부정맥)", "심장", AGG_SUM, ("심장질환", "특정Ⅰ")),
    ProposalRule("상해수술비", "수술", AGG_SUM, ("상해수술비",), excludes=("화상", "외모특정")),
    ProposalRule("질병수술비", "수술", AGG_SUM, ("질병수술비",), excludes=("대질병",)),
    ProposalRule("뇌혈관질환수술비", "수술", AGG_SUM, ("뇌혈관", "수술비")),
    ProposalRule("허혈성심장질환수술비", "수술", AGG_SUM, ("심장질환", "수술비")),
    ProposalRule("골절진단비", "골절", AGG_SUM, ("골절진단비",)),
    ProposalRule("깁스치료비", "골절", AGG_SUM, ("깁스치료비",)),
    ProposalRule("가족/일상/자녀배상", "배상책임", AGG_REP, ("일상생활중배상책임",)),
    ProposalRule("가족/일상/자녀배상", "배상책임", AGG_REP, ("가족일상", "배상")),
    ProposalRule("교통사고처리지원금", "운전자", AGG_SUM, ("교통사고처리지원금",), excludes=("6주미만",)),
    ProposalRule("교통사고처리지원금(6주미만)", "운전자", AGG_SUM, ("6주미만", "교통사고처리지원금")),
    ProposalRule("변호사선임비용", "운전자", AGG_SUM, ("변호사선임",)),
    ProposalRule("벌금(대인/스쿨존/대물)", "운전자", AGG_SUM, ("벌금",)),
)


PRODUCT_PROFILES: tuple[ProductProfile, ...] = (
    ProductProfile(
        "meritz-alpha",
        "메리츠화재",
        "(무)메리츠 The좋은알파Plus종합보장보험2604",
        ("The좋은알파Plus", "좋은알파Plus", "알파Plus종합"),
        56_950,
        fallback_coverages=(
            RegistryCoverage("상해사망", 100_000_000, "사망", AGG_SUM, "종합 제안서 실측"),
            RegistryCoverage("상해80%미만후유장해", 100_000_000, "후유장해", AGG_SUM, "종합 제안서 실측"),
            RegistryCoverage("상해수술비", 1_000_000, "수술", AGG_SUM, "종합 제안서 실측"),
            RegistryCoverage("질병수술비", 200_000, "수술", AGG_SUM, "종합 제안서 실측"),
            RegistryCoverage("뇌혈관질환", 10_000_000, "뇌", AGG_SUM, "회사 내부 대표값"),
            RegistryCoverage("허혈성심장질환", 10_000_000, "심장", AGG_SUM, "회사 내부 대표값"),
            RegistryCoverage("골절진단비", 300_000, "골절", AGG_SUM, "종합 제안서 실측"),
            RegistryCoverage("깁스치료비", 500_000, "골절", AGG_SUM, "종합 제안서 실측"),
            RegistryCoverage("가족/일상/자녀배상", 100_000_000, "배상책임", AGG_REP, "대표 배상책임"),
        ),
        bundle_coverages=(
            RegistryCoverage("뇌혈관질환수술비", 20_000_000, "수술", AGG_SUM, "특정순환계질환 통합치료비 분해"),
            RegistryCoverage("허혈성심장질환수술비", 20_000_000, "수술", AGG_SUM, "특정순환계질환 통합치료비 분해"),
        ),
    ),
    ProductProfile(
        "meritz-cancer",
        "메리츠화재",
        "(무)메리츠 또걸려도또받는암보험(연만기형)2601",
        ("또걸려도또받는암", "또받는암보험"),
        35_070,
        fallback_coverages=(
            RegistryCoverage("일반암", 50_000_000, "암", AGG_SUM, "암종별통합암진단 대표값"),
            RegistryCoverage("유사암", 10_000_000, "암", AGG_SUM, "또또암 유사암"),
        ),
        bundle_coverages=(
            RegistryCoverage("암수술비", 17_500_000, "수술", AGG_SUM, "암 통합치료비 bundle 분해"),
            RegistryCoverage("고액(표적)항암치료비", 80_500_000, "암", AGG_SUM, "암 통합치료비 bundle 분해"),
            RegistryCoverage("항암방사선약물치료", 20_500_000, "암", AGG_SUM, "암 통합치료비 bundle 분해"),
        ),
    ),
    ProductProfile(
        "meritz-driver",
        "메리츠화재",
        "(무)메리츠 운전자상해종합보험2604",
        ("운전자상해종합보험", "운전자상해"),
        12_320,
        fallback_coverages=(
            RegistryCoverage("교통사고처리지원금", 200_000_000, "운전자", AGG_SUM, "운전자 제안서 실측"),
            RegistryCoverage("변호사선임비용", 5_000_000, "운전자", AGG_SUM, "운전자 제안서 실측"),
            RegistryCoverage("벌금(대인/스쿨존/대물)", 30_000_000, "운전자", AGG_SUM, "운전자 제안서 실측"),
            RegistryCoverage("교통사고처리지원금(6주미만)", 10_000_000, "운전자", AGG_SUM, "운전자 제안서 실측"),
            RegistryCoverage("자동차사고부상", 300_000, "운전자", AGG_SUM, "14급 기준 대표값"),
        ),
    ),
    ProductProfile(
        "mirae-mcare",
        "미래에셋생명",
        "미래에셋 M-케어 건강보험(갱신형)",
        ("M-케어", "M케어", "미래에셋"),
        36_874,
        fallback_coverages=(
            RegistryCoverage("상해사망", 20_000_000, "사망", AGG_SUM, "미래 재해사망"),
            RegistryCoverage("일반암", 100_000_000, "암", AGG_SUM, "미래 암진단"),
            RegistryCoverage("유사암", 20_000_000, "암", AGG_SUM, "미래 유사암 직접 추출"),
        ),
    ),
    ProductProfile(
        "kb-hope",
        "KB손해보험",
        "KB 금쪽같은 희망플러스 건강보험",
        ("금쪽같은 희망플러스", "희망플러스 건강보험"),
        20_940,
        fallback_coverages=(
            RegistryCoverage("상해사망", 1_000_000, "사망", AGG_SUM, "KB 기본계약"),
            RegistryCoverage("상해80%미만후유장해", 1_000_000, "후유장해", AGG_SUM, "KB 기본계약"),
            RegistryCoverage("뇌혈관질환", 30_000_000, "뇌", AGG_SUM, "KB 뇌혈관질환"),
            RegistryCoverage("허혈성심장질환", 10_000_000, "심장", AGG_SUM, "KB 허혈성"),
            RegistryCoverage("급성심근경색증", 50_000_000, "심장", AGG_SUM, "KB 심장질환 특정Ⅱ"),
            RegistryCoverage("심장질환(부정맥)", 20_000_000, "심장", AGG_SUM, "KB 심장질환 특정Ⅰ"),
        ),
    ),
)
