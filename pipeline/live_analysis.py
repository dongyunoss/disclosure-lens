"""Conservative automatic analysis of a single regular filing and its comparative columns."""
import re
import os
from .core import COMPANIES, calculate, parse_amount, now, digest, save
from .drivers import fcf_bridge, validate_analysis
from .parse import parse_report

# Exact identifiers/names only. Ambiguous or missing company-specific concepts stay pending.
ACCOUNTS = {
    'cfo': ({'ifrs-full_CashFlowsFromUsedInOperatingActivities'}, {'영업활동현금흐름','영업활동으로인한현금흐름','영업활동으로부터의현금흐름'}, {'CF'}),
    'ppe': ({'ifrs-full_PurchaseOfPropertyPlantAndEquipment'}, {'유형자산의취득','유형자산취득'}, {'CF'}),
    'intangibles': ({'ifrs-full_PurchaseOfIntangibleAssets'}, {'무형자산의취득','무형자산취득'}, {'CF'}),
    'revenue': ({'ifrs-full_Revenue'}, {'매출액','수익(매출액)'}, {'IS','CIS'}),
}


def account_pair(rows, key, filing):
    ids,names,statements=ACCOUNTS[key]
    found=[r for r in rows if r.get('sj_div') in statements and
           (r.get('account_id') in ids or re.sub(r'\s+','',r.get('account_nm','')) in names)]
    if len(found)!=1:raise ValueError(key+' 계정이 없거나 중복됩니다. 회사별 매핑을 검토하세요.')
    row=found[0]
    if (row.get('rcept_no')!=filing['receipt'] or str(row.get('bsns_year'))!=str(filing['year']) or
        row.get('reprt_code')!=filing['reportCode'] or row.get('currency')!='KRW' or row.get('fs_div','CFS')!='CFS'):
        raise ValueError('재무 API 접수번호·회계연도·기간·통화·연결 기준 불일치')
    annual=filing['reportCode']=='11011'
    if not annual and key=='revenue':
        current,prior='thstrm_add_amount','frmtrm_add_amount'
    else:
        current,prior='thstrm_amount',('frmtrm_amount' if annual else 'frmtrm_q_amount')
    a,b=parse_amount(row.get(prior,'')),parse_amount(row.get(current,''))
    if key in {'ppe','intangibles'}:a,b=str(abs(int(a))),str(abs(int(b)))
    quote=f"{row['account_nm']} | {prior}: {row[prior]} | {current}: {row[current]}"
    return a,b,dict(id=key,quote=quote,sourceUrl=filing['url'],section='OpenDART 연결 전체 재무제표 · '+row['sj_div'],
                   unit='원',columns=['전년 동기 누적','당기 누적'],accountId=row.get('account_id',''),receipt=filing['receipt'])


def analyze(root, client, filing):
    folder=root/'private/live'/filing['receipt']
    folder.mkdir(parents=True,exist_ok=True)
    archive=folder/'source.zip'
    if not archive.exists():archive.write_bytes(client.request('document.xml',rcept_no=filing['receipt']))
    raw=archive.read_bytes()
    rows=client.request('fnlttSinglAcntAll.json',corp_code=filing['corpCode'],bsns_year=filing['year'],reprt_code=filing['reportCode'],fs_div='CFS')['list']
    save(folder/'accounts.json',rows)
    evidence=[];limitations=[];pairs={}
    for key in ACCOUNTS:
        try:
            a,b,ref=account_pair(rows,key,filing);pairs[key]=(a,b);evidence.append(ref)
        except ValueError as exc:limitations.append(str(exc))
    metrics=[]
    if all(k in pairs for k in ('cfo','ppe','intangibles')):
        metrics.append(fcf_bridge({k:pairs[k][0] for k in ('cfo','ppe','intangibles')},
                                  {k:pairs[k][1] for k in ('cfo','ppe','intangibles')},
                                  {k:[k] for k in ('cfo','ppe','intangibles')}))
    if 'revenue' in pairs:
        metrics.append(dict(id='revenue',label='매출',**calculate(*pairs['revenue']),components=[],residual=None,
                            evidence=['revenue'],definition='전년 동기 대비 누적 연결 매출',
                            caveat='지역·제품별 비교 수치가 검증되지 않아 매출 변화 원인은 보류했습니다.'))
    if not metrics:raise ValueError('비교 가능한 재무 계정이 아직 없습니다. 재무 API 갱신 후 재시도합니다.')
    try:
        blocks=parse_report(raw,dict(id=filing['receipt']))
        if 'revenue' in pairs:
            from .regions import extract_regions
            regional=extract_regions(blocks,filing,*pairs['revenue'])
            if regional:
                metric,ref=regional
                metrics=[metric if m['id']=='revenue' else m for m in metrics];evidence.append(ref)
        candidates=[b for b in blocks if b['kind']=='paragraph' and
                    any(w in b['text'] for w in ['매출','현금흐름','설비투자','자본지출']) and
                    any(w in b['text'] for w in ['증가','감소','영향','기인'])]
        # Candidates are saved for human review; keyword proximity is not causal evidence.
        save(folder/'reason-candidates.json',candidates)
        if candidates and all(os.getenv(k) for k in ('LLM_API_KEY','LLM_MODEL','LLM_BASE_URL')):
            from .reasons import draft
            try:draft(root,folder,filing,candidates,metrics)
            except ValueError:limitations.append('AI 원인 설명은 응답·근거·비용 검증을 통과하지 못해 보류했습니다. 숫자 계산은 유지합니다.')
        limitations.append('회사 설명 후보는 비공개 검수 파일에 저장했습니다. 인과관계 확인 전에는 원인으로 공개하지 않습니다.')
    except ValueError:
        limitations.append('원문 구조를 식별하지 못해 서술 원인 추출을 보류했습니다.')
    year,month=filing['year'],filing['month']
    end={3:'03.31',6:'06.30',9:'09.30',12:'12.31'}[month]
    result=dict(schemaVersion=1,id=filing['companyId']+'-'+filing['receipt'],companyId=filing['companyId'],
        companyName=COMPANIES[filing['companyId']][0],title=filing['title'],status='automatic',generatedAt=now(),
        periodBefore=f'{year-1}.01.01–{year-1}.{end}',periodAfter=f'{year}.01.01–{year}.{end}',basis='연결',currency='KRW',
        source=dict(title=filing['title'],url=filing['url'],sha256=digest(raw),filedAt=filing['filedAt'],checkedAt=now(),latestCorrectionVerified=False),
        comparisonNote='현재 접수 보고서의 전년 동기 누적 비교열을 사용합니다. 직전 분기와 혼합하지 않습니다. API 수치는 원문 전수 검수 전입니다.',
        metrics=metrics,evidence=evidence,companyExplanations=[],limitations=limitations)
    validate_analysis(result);save(folder/'analysis.json',result)
    return result
