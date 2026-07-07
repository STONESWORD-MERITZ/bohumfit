"""리모델링 보장분석표 데이터 구조([전]/[최종]) — dataclass + dict 변환."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Contract:
    idx: int
    insurer: str
    product: str
    contract_date: Optional[str]
    pay_cycle: Optional[str]
    pay_years: Optional[int]
    pay_months: Optional[int]
    maturity: Optional[str]
    monthly_premium: Optional[int]
    remark: Optional[str] = None  # 계약 특이사항 비고(계피상이 등, 값 아님)

    @property
    def paid_total(self) -> Optional[int]:
        if self.monthly_premium is None or self.pay_months is None:
            return None
        return self.monthly_premium * self.pay_months

    def to_dict(self) -> dict:
        d = asdict(self)
        d["paid_total"] = self.paid_total
        return d


@dataclass
class Customer:
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None


def before_coverage(kb_name, kb_group, group12, agg, summary, by_company, enrolled) -> dict:
    return {
        "kb_name": kb_name, "kb_group": kb_group, "group12": group12, "agg": agg,
        "summary": summary, "by_company": by_company, "enrolled": enrolled,
    }


def final_coverage(group12, kb_name, agg, value, recommended, gap, status) -> dict:
    return {
        "group12": group12, "kb_name": kb_name, "agg": agg, "value": value,
        "recommended": recommended, "gap": gap, "status": status,
    }
