from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SCHEMA_VERSION = 1
PROMPT_VERSION = 'evidence-alignment-v1'
COMPANIES = {'samsung':('삼성전자','005930'), 'skhynix':('SK하이닉스','000660'), 'lge':('LG전자','066570')}
TARGET_SECTIONS = ('사업의 개요','사업 개요','주요 제품','주요제품','주요 서비스')

def now(): return datetime.now(timezone.utc).isoformat()
def digest(value):
    raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)
def normalized(text):return ' '.join(text.split())
def is_target(block):return block['kind']=='paragraph' and any(s in block['section'] for s in TARGET_SECTIONS)

def parse_amount(value: str, multiplier=1):
    raw=value.strip().replace(',','').replace(' ','').replace('−','-').replace('△','-')
    if raw.startswith('(') and raw.endswith(')'):raw='-'+raw[1:-1]
    if not re.fullmatch(r'-?\d+(?:\.\d+)?',raw):raise ValueError(f'유효한 금액이 아닙니다: {value!r}')
    amount=Decimal(raw)*Decimal(str(multiplier))
    if not amount.is_finite() or amount!=amount.to_integral_value():raise ValueError('원 단위 정수로 변환할 수 없습니다.')
    return str(int(amount))

def calculate(before:str,after:str,*,prior_comparative=None,compatible=True):
    a,b=Decimal(before),Decimal(after)
    if not a.is_finite() or not b.is_finite() or a!=a.to_integral_value() or b!=b.to_integral_value():raise ValueError('금액은 원 단위 정수여야 합니다.')
    delta=b-a;reason=None
    if not compatible:reason='비교 기준 차이: 증감률 보류'
    elif prior_comparative is not None and Decimal(prior_comparative)!=a:reason='전기 비교 수치 재작성: 증감률 보류'
    if a<0<b:status='흑자 전환'
    elif a>0>b:status='적자 전환'
    elif a<0 and b<0:status='적자 확대' if b<a else '적자 축소' if b>a else '변동 없음'
    elif delta>0:status='증가'
    elif delta<0:status='감소'
    else:status='변동 없음'
    pct=str((delta/a*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) if a>0 and not reason else None
    if reason:status='증감률 보류'
    elif a==0:reason='이전 값이 0이므로 증감률 미표시'
    return dict(before=str(int(a)),after=str(int(b)),delta=str(int(delta)),percent=pct,status=status,reason=reason)

def validate_change(change,blocks,before_report,after_report):
    if change['kind'] not in {'content','added','removed','wording','uncertain'}:raise ValueError('알 수 없는 변화 유형')
    if not isinstance(change.get('title'),str) or not change['title'].strip() or not isinstance(change.get('explanation'),str) or not change['explanation'].strip():raise ValueError('설명과 제목이 필요합니다.')
    for side,report in [('before',before_report),('after',after_report)]:
        for ref in change[side]:
            b=blocks.get(ref['blockId'])
            if not b or b['reportId']!=report:raise ValueError('근거가 대응 보고서에 속하지 않습니다.')
            if not is_target(b):raise ValueError('서술 근거가 분석 범위 밖입니다.')
            if not isinstance(ref['quote'],str) or not ref['quote'].strip() or ref['quote'] not in b['text']:raise ValueError('인용문이 원문에 존재하지 않습니다.')
    if not change['before'] and not change['after']:raise ValueError('근거 없는 설명은 허용되지 않습니다.')
    kind=change['kind']
    if kind in {'content','wording'} and (not change['before'] or not change['after']):raise ValueError('변경에는 양쪽 근거가 필요합니다.')
    if kind=='added' and (change['before'] or not change['after']):raise ValueError('추가 판정 근거 오류')
    if kind=='removed' and (not change['before'] or change['after']):raise ValueError('삭제 판정 근거 오류')
    if kind in {'added','removed'}:
        side='after' if kind=='added' else 'before'; opposite=before_report if kind=='added' else after_report
        for ref in change[side]:
            text=normalized(blocks[ref['blockId']]['text'])
            if any(b['reportId']==opposite and is_target(b) and normalized(b['text'])==text for b in blocks.values()):raise ValueError('다른 위치의 동일 문단을 추가·삭제로 판정할 수 없습니다.')

def validate_public(data,*,allow_demo=False):
    if data.get('schemaVersion')!=1:raise ValueError('지원하지 않는 데이터 계약')
    if data.get('mode')=='demo':
        if allow_demo:return
        raise ValueError('가상 예시를 실제 공시로 공개할 수 없습니다.')
    if data.get('mode')!='reviewed':raise ValueError('검수되지 않은 결과입니다.')
    if data['companyId'] not in COMPANIES or len(data['reports'])!=2:raise ValueError('지원하지 않는 기업 또는 보고서 쌍')
    old,new=data['reports']
    if [old['year'],new['year']]!=[2024,2025]:raise ValueError('지원 연도는 2024·2025입니다.')
    for r in data['reports']:
        if r['companyId']!=data['companyId'] or not re.fullmatch(r'\d{14}',r['receipt'] or ''):raise ValueError('유효한 보고서 접수번호가 필요합니다.')
        if r['dartUrl']!=f'https://dart.fss.or.kr/dsaf001/main.do?rcpNo={r["receipt"]}':raise ValueError('잘못된 DART 링크')
        if not re.fullmatch('[0-9a-f]{64}',r['sha256']) or not r['checkedAt'] or not r['filedAt']:raise ValueError('원문 보존 정보가 없습니다.')
    blocks={b['id']:b for b in data['evidence']}
    if len(blocks)!=len(data['evidence']):raise ValueError('중복 근거 ID')
    if any(b['reportId'] not in {old['id'],new['id']} for b in blocks.values()):raise ValueError('다른 보고서의 근거가 포함되어 있습니다.')
    ids=[x['id'] for x in data['changes']+data['financials']]
    if len(ids)!=len(set(ids)):raise ValueError('중복 변경점 ID')
    for c in data['changes']:
        validate_change(c,blocks,old['id'],new['id'])
        if c['reviewStatus'] not in {'approved','needs_review'}:raise ValueError('잘못된 검수 상태')
        if c['reviewStatus']=='needs_review' and c['kind']!='uncertain':raise ValueError('미검수 설명은 공개할 수 없습니다.')
    if {f['id'] for f in data['financials']}!={'revenue','operating_income'} or len(data['financials'])!=2:raise ValueError('두 재무계정 모두 필요합니다.')
    for f in data['financials']:
        if f['currency']!='KRW' or f['basis']!='CFS':raise ValueError('통화·연결 기준 불일치')
        for side,r in [('before',old),('after',new)]:
            b=blocks.get(f[side+'BlockId'])
            if not b or b['reportId']!=r['id'] or b['kind']!='table':raise ValueError('재무 근거 표 누락')
        expected=calculate(f['before'],f['after'],prior_comparative=f.get('priorComparative'),compatible=f.get('compatible',True))
        if any(f[k]!=expected[k] for k in expected):raise ValueError('재무 계산 불일치')
