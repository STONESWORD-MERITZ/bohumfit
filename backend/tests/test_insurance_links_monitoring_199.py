# -*- coding: utf-8 -*-
"""BOHUMFIT-199/200 보험사 완전판매 모니터링 링크 화면 연결 회귀 테스트."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "pages" / "InsuranceLinks.tsx"


def test_insurance_links_complete_sale_monitoring_links():
    src = SRC.read_text(encoding="utf-8")

    assert "monitoringUrl?: string" in src
    assert "monitoringNote?: string" in src
    assert 'type MonitoringAccess = "direct" | "auth" | "path" | "none"' in src
    assert "const hasMonitoringUrl = isExternalUrl(ins.monitoringUrl)" in src
    assert "openUrl(ins.monitoringUrl)" in src
    assert "완전판매 모니터링 링크 확인이 필요합니다." in src
    assert "본인인증 또는 로그인 후 모니터링 대상계약으로 이동합니다." in src
    assert "메인/로그인 화면으로 열리면 상세보기의 모니터링 경로를 따라가 주세요." in src
    assert '<ContactRow label="완전판매 모니터링" value={ins.monitoringUrl} />' in src
    assert '<ContactRow label="모니터링 경로" value={ins.monitoringPath} />' in src
    assert "applyMonitoringAudit" in src
    assert ".map(applyMonitoringAudit)" in src

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

    audit = re.search(
        r"const MONITORING_AUDIT: Record<string, MonitoringAudit> = \{(.*?)\n\};",
        src,
        re.S,
    )
    assert audit, "MONITORING_AUDIT block not found"
    audit_src = audit.group(1)
    audit_entries = re.findall(r"^  [^{}\n]+: \{", audit_src, re.M)
    assert len(audit_entries) == 44
    assert audit_src.count('monitoringAccess: "direct"') == 16
    assert audit_src.count('monitoringAccess: "auth"') == 2
    assert audit_src.count('monitoringAccess: "path"') == 20
    assert audit_src.count('monitoringAccess: "none"') == 6

    for official_url in [
        "https://m.hanwhalife.com/main/insurance/newContMon/IN_NWMO000_P01000.do",
        "https://www.kdblife.com/scrId/INLNB004M01P.do",
        "https://www.heungkukfire.co.kr/CNW/fullSalesAgree.do",
        "https://ir.idbins.com/FWMYCV0436.do?rUrl=/FWMYCV0438.do",
        "https://www.kbinsure.co.kr/CG110020001.ec",
        "https://cyber.shinhanlife.co.kr/",
        "https://cyber.abllife.co.kr/",
        "https://www.kyobo.com/dgt/web/insurance/monitoring/direct/cnr/list",
        "https://mhappycall.kblife.co.kr/",
        "https://m.lina.co.kr/cyber/contract/happycall",
        "https://www.samsungfire.com/mysf/P_P01_02_04_255.html",
        "https://www.aig.co.kr/wt/dpwtm100.html?menuId=MS243",
        "https://www.nhfire.co.kr/mypage/membership/eMonitoringIntro.nhfire",
    ]:
        assert official_url in src

    for routed_insurer in [
        "메리츠화재",
        "한화손해보험",
        "신한라이프",
        "흥국생명",
        "동양생명",
        "ABL생명",
        "DB생명",
    ]:
        assert routed_insurer in audit_src

    for route_hint in [
        "사이버창구 로그인 > 보험계약조회 > 해피콜결과조회",
        "모바일/앱 로그인 > 계약조회/계약관리 > 해피콜 결과 조회 또는 완전판매 모니터링",
        "고객창구 로그인 > 계약관리 > 해피콜/완전판매 확인 또는 1588-3131 문의",
    ]:
        assert route_hint in audit_src
