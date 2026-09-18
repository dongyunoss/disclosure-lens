"""Build a reproducible arithmetic analysis from the retained official Samsung PDF."""
import re
from .core import load, save, digest, now, parse_amount
from .drivers import fcf_bridge, revenue_bridge, validate_analysis


def build(root):
    from pypdf import PdfReader
    source = next(x for x in load(root/'public/excerpts/library.json')['sources'] if x['id']=='samsung-2025')
    raw = (root/'private/official-pdf/samsung-2025.pdf').read_bytes()
    if digest(raw) != source['sha256']:
        raise ValueError('보관 PDF가 검증한 원본과 다릅니다.')
    reader = PdfReader(root/'private/official-pdf/samsung-2025.pdf')
    cash = reader.pages[88].extract_text()
    region = reader.pages[184].extract_text()
    if not all(s in cash for s in ('연결 현금흐름표','2025.01.01','2024.01.01','백만원')):
        raise ValueError('연결 현금흐름표 비교 기준 오류')
    if not all(s in region for s in ('순매출액의 지역별 공시', '당기 (단위 : 백만원)', '전기 (단위 : 백만원)')):
        raise ValueError('지역별 매출표 비교 기준 오류')
    evidence = []
    def reference(ident, quote, page, section, columns):
        evidence.append(dict(id=ident, quote=quote, sourceUrl=source['url']+'#page='+str(page),
                             section=section, page=page, unit='백만원', columns=columns))
        return ident
    before, after, refs = {}, {}, {}
    for key,label in [('cfo','영업활동현금흐름'), ('ppe','유형자산의 취득'), ('intangibles','무형자산의 취득')]:
        lines = [line.strip() for line in cash.splitlines() if line.strip().startswith(label)]
        if len(lines)!=1: raise ValueError('현금흐름 행을 유일하게 식별하지 못했습니다.')
        values = re.findall(r'\(?\d{1,3}(?:,\d{3})+\)?', lines[0])
        if len(values)!=3: raise ValueError('현금흐름 열 개수 오류')
        amounts = [int(parse_amount(v, 1000000)) for v in values]
        if key!='cfo':
            if any(v>0 for v in amounts): raise ValueError('취득 현금유출 부호 변경: 매핑 검토 필요')
            amounts = [-v for v in amounts]
        after[key], before[key] = str(amounts[0]), str(amounts[1])
        refs[key] = [reference(key,lines[0],89,'연결 현금흐름표',['2025','2024','2023'])]
    rows = [line.strip() for line in region.splitlines() if line.strip().startswith('순매출액 ')]
    if len(rows)!=2: raise ValueError('지역별 매출 행 오류')
    parsed = [re.findall(r'\d{1,3}(?:,\d{3})+', row) for row in rows]
    if any(len(row)!=6 for row in parsed): raise ValueError('지역별 열 개수 오류')
    labels=['국내','미주','유럽','아시아 및 아프리카','중국']
    for ident,row in zip(['region-after','region-before'],rows):
        reference(ident,row,185,'연결 주석 · 순매출액의 지역별 공시',labels+['합계'])
    current, prior = [[parse_amount(v,1000000) for v in row] for row in parsed]
    if sum(map(int,current[:-1]))!=int(current[-1]) or sum(map(int,prior[:-1]))!=int(prior[-1]):
        raise ValueError('지역 매출 합계가 연결 매출과 다릅니다.')
    segments=[dict(label=label,before=prior[i],after=current[i],evidence=['region-before','region-after']) for i,label in enumerate(labels)]
    analysis = validate_analysis(dict(schemaVersion=1,id='samsung-2025-drivers-v1',companyId='samsung',companyName='삼성전자',
        title='2025 사업보고서 · FCF와 매출 변화',status='automatic',generatedAt=now(),
        periodBefore='2024.01.01–2024.12.31',periodAfter='2025.01.01–2025.12.31',basis='연결',currency='KRW',
        source=dict(title='2025 사업보고서 (기업 공식 IR 게시본)',url=source['url'],sha256=source['sha256'],
                    filedAt=source['filedAt'],checkedAt=source['retrievedAt'],latestCorrectionVerified=False),
        comparisonNote='2025 보고서에 기재된 당기와 전기를 같은 기준으로 비교했습니다. 원래의 2024 보고서 수치와 다를 수 있습니다.',
        metrics=[fcf_bridge(before,after,refs),revenue_bridge(prior[-1],current[-1],segments,evidence=['region-before','region-after'])],
        evidence=evidence,companyExplanations=[],
        limitations=['공식 IR 게시본의 최종 정정 여부는 미확인입니다.',
                     '설비투자 목적과 가격·물량·환율별 매출 변화 원인은 확인된 설명이 없어 보류했습니다.']))
    from .table_overlays import attach
    attach(root,analysis)
    save(root/'public/drivers/samsung-2025-drivers-v1.json',analysis)
    catalog_path=root/'public/drivers/catalog.json'
    catalog=load(catalog_path) if catalog_path.exists() else dict(schemaVersion=1,items=[])
    entry=dict(id=analysis['id'],companyId='samsung',companyName='삼성전자',title=analysis['title'],
               path='drivers/samsung-2025-drivers-v1.json',status='automatic')
    catalog['items']=[entry]+[x for x in catalog['items'] if x['id']!=entry['id']]
    save(catalog_path,catalog)
    status=root/'public/drivers/monitor.json'
    if not status.exists():save(status,dict(schemaVersion=1,state='not_configured',checkedAt=None,intervalSeconds=300,
        message='공시 수집 인증키와 상시 실행 환경 연결 전입니다. 현재는 보관된 실제 보고서 분석을 제공합니다.',filings=[]))
    return analysis


if __name__=='__main__':
    from pathlib import Path
    build(Path(__file__).resolve().parents[1])
    print('실제 공시의 FCF·지역별 매출 기여도 생성 완료')
