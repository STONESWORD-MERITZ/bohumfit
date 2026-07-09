# -*- coding: utf-8 -*-
"""BOHUMFIT-199 보험사 링크 완전판매 모니터링 데이터/화면 연결 회귀 테스트."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "pages" / "InsuranceLinks.tsx"


def test_insurance_links_complete_sale_monitoring_links():
    src = SRC.read_text(encoding="utf-8")

    assert "monitoringUrl?: string" in src
    assert "monitoringNote?: string" in src
    assert "const hasMonitoringUrl = isExternalUrl(ins.monitoringUrl)" in src
    assert "openUrl(ins.monitoringUrl)" in src
    assert "완전판매 모니터링 링크 확인이 필요합니다." in src
    assert '<ContactRow label="완전판매 모니터링" value={ins.monitoringUrl} />' in src
    assert "보험사별 로그인·본인인증" in src

    block = re.search(r"const INSURANCE_DATA: Insurer\[] = \[(.*?)\];", src, re.S)
    assert block, "INSURANCE_DATA block not found"
    rows = re.findall(r"^\s*\{.*?\},\s*$", block.group(1), re.M)
    assert len(rows) == 44

    mutual_rows = [row for row in rows if 'category: "공제회사"' not in row]
    cooperative_rows = [row for row in rows if 'category: "공제회사"' in row]
    assert len(mutual_rows) == 38
    assert len(cooperative_rows) == 6
    assert all('monitoringUrl: "http' in row for row in mutual_rows)
    assert all("monitoringNote:" in row for row in mutual_rows)
    assert all("monitoringUrl:" not in row for row in cooperative_rows)
    assert all("직접 링크 없음" in row for row in cooperative_rows)

    for official_url in [
        "https://www.hanwhalife.com/nm.do",
        "https://www.kyobo.com/dgt/web/insurance/monitoring/direct/cnr/list",
        "https://mhappycall.kblife.co.kr/",
        "https://m.lina.co.kr/cyber/contract/happycall",
        "https://www.samsungfire.com/mysf/P_P01_02_04_255.html",
        "https://ir.idbins.com/FWMYCV0438.do",
        "https://www.aig.co.kr/wt/dpwtm100.html?menuId=MS243",
        "https://www.nhfire.co.kr/mypage/membership/eMonitoringIntro.nhfire",
    ]:
        assert official_url in src
