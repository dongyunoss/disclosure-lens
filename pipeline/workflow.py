from __future__ import annotations
import html
import os
import re
from pathlib import Path
from .align import candidate_packets
from .core import COMPANIES, PROMPT_VERSION, calculate, digest, is_target, load, now, parse_amount, save, validate_change, validate_public
from .parse import parse_report

def prepare(root,cid):
    entries=[e for e in load(root/'private'/'collection.json') if e['companyId']==cid]
    if sorted(e['year'] for e in entries)!=[2024,2025]:raise ValueError('두 회계연도의 보고서를 먼저 수집하세요.')
    reports=[];evidence=[];accounts={};sources=[]
    for entry in sorted(entries,key=lambda e:e['year']):
        report=load(root/entry['snapshot']/'report.json');raw=(root/entry['path']/'source.zip').read_bytes()
        if digest(raw)!=report['sha256']:raise ValueError('보관 원본의 해시가 일치하지 않습니다.')
        blocks=parse_report(raw,report)
        if not any(is_target(b) for b in blocks):raise ValueError('사업 개요·주요 제품 절을 찾지 못했습니다. 원본 구조를 확인하세요.')
        reports.append(report);evidence.extend(blocks);accounts[report['id']]=load(root/entry['snapshot']/'accounts.json');sources.append(entry)
    name,stock=COMPANIES[cid];pair=f'{cid}-2024-2025'
    data=dict(schemaVersion=1,id=pair,companyId=cid,companyName=name,stockCode=stock,mode='draft',version='pending',checkedAt=now(),reports=reports,financials=[],changes=[],evidence=evidence,analysis=dict(model='not-run',promptVersion=PROMPT_VERSION),coverage=['연결 매출','연결 영업이익','사업 개요','주요 제품·서비스'])
    folder=root/'private'/'work'/cid
    if (folder/'draft.json').exists():
        previous=load(folder/'draft.json');save(folder/'history'/f'{digest(previous)}.json',previous)
    save(folder/'draft.json',data);save(folder/'accounts.json',accounts);save(folder/'sources.json',sources)
    old=[b for b in evidence if b['reportId']==reports[0]['id']];new=[b for b in evidence if b['reportId']==reports[1]['id']]
    save(folder/'candidates.json',candidate_packets(old,new))
    save(folder/'bindings.template.json',{key:{'before':{'blockId':'','row':0,'column':1,'multiplier':1,'period':'2024-01-01/2024-12-31','apiMismatchReviewed':False},'after':{'blockId':'','row':0,'column':1,'priorColumn':2,'multiplier':1,'period':'2025-01-01/2025-12-31','apiMismatchReviewed':False},'compatible':True} for key in ['revenue','operating_income']})
    review_html(folder,data)
    return folder

def analyze(root,cid):
    from .llm import completion
    folder=root/'private'/'work'/cid;data=load(folder/'draft.json');blocks={b['id']:b for b in data['evidence']}
    changes=[];seen=set()
    for packet in load(folder/'candidates.json'):
        cache=folder/'llm-cache'/f'{digest(dict(packet=packet,model=os.getenv("LLM_MODEL"),promptVersion=PROMPT_VERSION))}.json'
        response=load(cache) if cache.exists() else completion(root,packet)
        if not isinstance(response.get('changes'),list):raise ValueError('LLM changes 배열이 없습니다.')
        for candidate in response['changes']:
            allowed={b['id'] for b in packet['before']+packet['after']}
            refs=candidate.get('before',[])+candidate.get('after',[])
            if any(ref['blockId'] not in allowed for ref in refs):raise ValueError('후보에 없는 LLM 근거 ID')
            # Allowlist fields prevents leaking prompts, provider metadata or internal notes.
            c={k:candidate[k] for k in ['kind','section','title','explanation','before','after']}
            c['reviewStatus']='needs_review'
            validate_change(c,blocks,data['reports'][0]['id'],data['reports'][1]['id'])
            key=digest(dict(before=c['before'],after=c['after']))
            if key in seen:continue
            seen.add(key);c['id']='change-'+key[:16];changes.append(c)
        if not cache.exists():save(cache,response)
    data['changes']=changes;data['analysis']['model']=os.getenv('LLM_MODEL','unknown');save(folder/'draft.json',data);review_html(folder,data)
    return len(changes)

ALIASES={'revenue':{'매출액','매출','수익(매출액)','영업수익'},'operating_income':{'영업이익','영업이익(손실)','영업손익','영업손실'}}

def bound_value(data,accounts,key,side,binding):
    report=data['reports'][0 if side=='before' else 1];blocks={b['id']:b for b in data['evidence']};b=blocks[binding['blockId']]
    if b['reportId']!=report['id'] or b['kind']!='table' or '연결' not in b['section']:raise ValueError('선택한 보고서의 연결 재무제표 표가 필요합니다.')
    year=report['year']
    if binding['period']!=f'{year}-01-01/{year}-12-31':raise ValueError('연간 회계기간을 확인하세요.')
    multiplier=binding['multiplier'];unit={1:'원',1000:'천원',1000000:'백만원',100000000:'억원'}.get(multiplier)
    context=re.sub(r'\s+','',' '.join([b['unit'],b['contextBefore'],b['contextAfter'],b['text']]))
    units=re.findall(r'단위[:：]?\(?((?:백만|천|억)?원)',context)
    if not unit or not units or any(found!=unit for found in units):raise ValueError('표의 명시된 단위와 변환 배수가 일치하지 않습니다.')
    row=b['rows'][binding['row']]
    if not any(re.sub(r'\s+','',''.join(cell)) in ALIASES[key] for cell in row):raise ValueError('선택한 표 행의 재무계정 명칭이 일치하지 않습니다.')
    value=parse_amount(row[binding['column']],multiplier)
    candidates=[a for a in accounts[report['id']] if a.get('fs_div')=='CFS' and a.get('reprt_code')=='11011' and a.get('bsns_year')==str(year) and re.sub(r'\s+','',a.get('account_nm','')) in ALIASES[key]]
    matched=any(a.get('rcept_no')==report['receipt'] and a.get('currency')=='KRW' and parse_amount(a['thstrm_amount'])==value for a in candidates if a.get('thstrm_amount'))
    if not matched and not binding.get('apiMismatchReviewed'):raise ValueError('재무 API와 원문이 불일치합니다. 원문 검수 후 apiMismatchReviewed를 명시하세요.')
    if side=='after':
        if binding['priorColumn']==binding['column']:raise ValueError('당기와 전기 열은 서로 달라야 합니다.')
        prior=parse_amount(row[binding['priorColumn']],multiplier)
    else:prior=None
    return value,prior

def assemble(root,cid):
    folder=root/'private'/'work'/cid;data=load(folder/'draft.json');bindings=load(folder/'bindings.json');accounts=load(folder/'accounts.json')
    financials=[]
    for key,label in [('revenue','매출'),('operating_income','영업이익')]:
        binding=bindings[key];a,_=bound_value(data,accounts,key,'before',binding['before']);b,prior=bound_value(data,accounts,key,'after',binding['after'])
        financials.append(dict(id=key,label=label,**calculate(a,b,prior_comparative=prior,compatible=binding['compatible']),priorComparative=prior,compatible=binding['compatible'],beforeBlockId=binding['before']['blockId'],afterBlockId=binding['after']['blockId'],currency='KRW',basis='CFS',beforeRow=binding['before']['row'],afterRow=binding['after']['row']))
    data['financials']=financials;save(folder/'draft.json',data);review_html(folder,data);return data

def verify_sources(root,cid,data):
    folder=root/'private'/'work'/cid
    expected=[];expected_reports=[]
    for entry in load(folder/'sources.json'):
        raw=(root/entry['path']/'source.zip').read_bytes();report=load(root/entry['snapshot']/'report.json')
        if digest(raw)!=report['sha256']:raise ValueError('원본 파일이 변경되었습니다.')
        expected.extend(parse_report(raw,report));expected_reports.append(report)
    if data['reports']!=expected_reports or data['evidence']!=expected:raise ValueError('초안의 원문·보고서 정보가 보관 원본과 다릅니다. prepare부터 다시 실행하세요.')

def review(root,cid,reviewer,acknowledged):
    if not reviewer.strip() or not acknowledged:raise ValueError('실제 검수자 이름과 검수 확인이 필요합니다.')
    folder=root/'private'/'work'/cid;data=load(folder/'draft.json');verify_sources(root,cid,data)
    # Do not silently approve or rewrite individual changes: operator edits reviewStatus explicitly.
    public=dict(data,mode='reviewed',version='review-check')
    validate_public(public)
    save(folder/'approval.json',dict(reviewer=reviewer,at=now(),draftHash=digest(data),bindingsHash=digest(load(folder/'bindings.json')),confirmed=True))

def public_payload(data,version):
    """Strict serialization allowlist. No internal notes, credentials, or review identities."""
    def pick(obj,keys):return {k:obj[k] for k in keys if k in obj}
    out=pick(data,['schemaVersion','id','companyId','companyName','stockCode','checkedAt','coverage'])
    out.update(mode='reviewed',version=version)
    out['reports']=[pick(r,['id','companyId','year','receipt','filedAt','corrected','checkedAt','sha256','dartUrl']) for r in data['reports']]
    out['financials']=[pick(f,['id','label','before','after','delta','percent','status','reason','beforeBlockId','afterBlockId','beforeRow','afterRow','currency','basis','priorComparative','compatible']) for f in data['financials']]
    out['changes']=[pick(c,['id','kind','section','title','explanation','before','after','reviewStatus']) for c in data['changes']]
    for c in out['changes']:
        for side in ['before','after']:c[side]=[pick(r,['blockId','quote']) for r in c[side]]
        if c['reviewStatus']=='needs_review':
            c.update(kind='uncertain',title='문단 대응 확인 필요',explanation='양쪽 문단의 대응 관계가 확정되지 않았습니다. 원문을 직접 확인하세요.')
    used={c['blockId'] for change in out['changes'] for c in change['before']+change['after']}|{f[k] for f in out['financials'] for k in ['beforeBlockId','afterBlockId']}
    out['evidence']=[pick(b,['id','reportId','kind','section','order','text','normalized','contextBefore','contextAfter','headers','rows','unit']) for b in data['evidence'] if b['id'] in used]
    out['analysis']=pick(data['analysis'],['model','promptVersion'])
    return out

def publish(root,cid):
    folder=root/'private'/'work'/cid;data=load(folder/'draft.json');approval=load(folder/'approval.json');bindings=load(folder/'bindings.json')
    if not approval.get('confirmed') or digest(data)!=approval['draftHash'] or digest(bindings)!=approval['bindingsHash']:raise ValueError('검수 이후 데이터가 변경되었습니다. 재검수가 필요합니다.')
    verify_sources(root,cid,data)
    # Recompute financials from original table bindings, never trust hand-edited result strings.
    reconstructed=assemble(root,cid)
    if digest(reconstructed)!=digest(data):raise ValueError('수치 계산이나 초안이 변경되었습니다. 재검수가 필요합니다.')
    from .release import release_gate
    release_gate(root,data)
    version=digest(data)[:20];out=public_payload(data,version);validate_public(out)
    relative=f'data/{cid}/{version}.json';dest=root/'public'/relative
    if dest.exists() and load(dest)!=out:raise ValueError('기존 공개본을 덮어쓸 수 없습니다.')
    if not dest.exists():save(dest,out)
    catalog=load(root/'public'/'data'/'catalog.json')
    company=next(c for c in catalog['companies'] if c['id']==cid)
    company['comparisons']=[dict(id=data['id'],years=[2024,2025],path=relative,mode='reviewed')]
    # Catalog pointer is updated only after the complete version was validated and saved.
    save(root/'public'/'data'/'catalog.json',catalog)
    return relative

def review_html(folder,data):
    esc=lambda x:html.escape(str(x),quote=True)
    parts=['<!doctype html><html lang="ko"><meta charset="utf-8"><title>공시렌즈 비공개 검수 자료</title><style>body{font:16px/1.8 system-ui;max-width:1200px;margin:40px auto;padding:20px;color:#20334a}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f9;padding:20px}article{border:1px solid #dae3eb;padding:24px;margin:20px 0}code{color:#067c70}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}</style>']
    parts.append(f'<h1>{esc(data["companyName"])} · 비공개 검수 자료</h1><p>금액·단위·기간·접수번호, 문단 이동·분할·병합, 서술의 근거를 확인하세요. 모든 항목 검수 후에만 review 명령으로 확인합니다.</p>')
    parts.append('<h2>변경점과 재무 비교</h2><pre>'+esc(__import__('json').dumps(dict(financials=data['financials'],changes=data['changes']),ensure_ascii=False,indent=2))+'</pre>')
    parts.append('<h2>원문 인덱스 · 행과 열은 0부터 시작</h2>')
    for b in data['evidence']:
        if not is_target(b) and b['kind']!='table':continue
        parts.append(f'<article id="{esc(b["id"])}"><code>{esc(b["id"])}</code><h3>{esc(b["section"])}</h3><p>{esc(b["contextBefore"])}</p>')
        if b['kind']=='table':
            parts.append('<table><thead><tr><th>행</th>'+''.join(f'<th>{i}: {esc(x)}</th>' for i,x in enumerate(b['headers']))+'</tr></thead><tbody>')
            parts.extend('<tr><th>'+str(i)+'</th>'+''.join('<td>'+esc(cell)+'</td>' for cell in row)+'</tr>' for i,row in enumerate(b['rows']))
            parts.append('</tbody></table><p>'+esc(b['unit'])+'</p>')
        else:parts.append('<pre>'+esc(b['text'])+'</pre>')
        parts.append('<p>'+esc(b['contextAfter'])+'</p></article>')
    parts.append('</html>');(folder/'review.html').write_text('\n'.join(parts),encoding='utf-8')
