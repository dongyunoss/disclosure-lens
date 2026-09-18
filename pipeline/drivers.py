"""Exact arithmetic attribution. Accounting contributions are not business causes."""
from decimal import Decimal, ROUND_HALF_UP
import re
from .core import calculate

FCF_DEFINITION = 'FCF = 영업활동현금흐름 − 유형자산 취득 현금지출 − 무형자산 취득 현금지출'


def integer(value):
    if not isinstance(value, str) or not re.fullmatch(r'-?\d+', value):
        raise ValueError('금액은 원 단위 정수 문자열이어야 합니다.')
    return int(value)


def contribution(label, before, after, direction=1, evidence=None):
    a, b = integer(before), integer(after)
    return dict(label=label, before=str(a), after=str(b), delta=str(b-a),
                impact=str((b-a)*direction), evidence=evidence or [])


def fcf_bridge(before, after, evidence=None):
    keys = ('cfo', 'ppe', 'intangibles')
    for snapshot in (before, after):
        if any(snapshot.get(k) is None for k in keys):
            raise ValueError('현금흐름 또는 자본지출 누락: FCF 계산을 보류합니다.')
        if any(integer(snapshot[k]) < 0 for k in ('ppe', 'intangibles')):
            raise ValueError('자본지출은 취득 현금유출의 양수 금액이어야 합니다.')
    a = integer(before['cfo'])-integer(before['ppe'])-integer(before['intangibles'])
    b = integer(after['cfo'])-integer(after['ppe'])-integer(after['intangibles'])
    refs = evidence or {}
    parts = [contribution(label, before[k], after[k], sign, refs.get(k, []))
             for k, label, sign in [('cfo', '영업현금흐름 변화', 1),
                                    ('ppe', '유형자산 취득 지출 변화', -1),
                                    ('intangibles', '무형자산 취득 지출 변화', -1)]]
    assert sum(integer(x['impact']) for x in parts) == b-a
    return dict(id='fcf', label='잉여현금흐름 (FCF)', **calculate(str(a), str(b)),
                definition=FCF_DEFINITION, components=parts, residual='0',
                caveat='회사 발표 FCF와 정의가 다를 수 있습니다. 자산 처분·사업결합·비현금 취득은 차감하지 않습니다. 산술적 분해이며 지출 목적을 단정하지 않습니다.')


def revenue_bridge(before, after, segments, *, comparable=True, evidence=None):
    a, b = integer(before), integer(after)
    if not comparable:
        raise ValueError('지역·사업부 분류 기준이 달라 기여도 계산을 보류합니다.')
    names = [s['label'] for s in segments]
    if len(names) != len(set(names)):
        raise ValueError('중복 구분으로 매출을 이중 집계할 수 없습니다.')
    parts = [contribution(s['label'], s['before'], s['after'], evidence=s.get('evidence')) for s in segments]
    # Never force an incomplete geographic/product breakdown to add up to total sales.
    residual_before = a-sum(integer(x['before']) for x in parts)
    residual_after = b-sum(integer(x['after']) for x in parts)
    if residual_before or residual_after:
        parts.append(contribution('미분류·조정 차이', str(residual_before), str(residual_after)))
    for part in parts:
        part['share'] = str((Decimal(part['impact'])/Decimal(b-a)*100).quantize(Decimal('.1'), rounding=ROUND_HALF_UP)) if b != a else None
    return dict(id='revenue', label='매출', **calculate(before, after),
                definition='같은 기준의 지역별 매출 증감액을 전체 매출 증감액과 대조합니다.',
                components=parts, residual=str(residual_after-residual_before), evidence=evidence or [],
                caveat='지역 매출과 수출액은 다릅니다. 가격·물량·환율·연결범위 영향은 별도 근거 없이는 구분할 수 없습니다. 지역별 분석과 제품별 분석은 서로 더하지 않습니다.')


def validate_analysis(item):
    if item.get('schemaVersion') != 1 or item.get('status') not in {'automatic', 'source_pending'}:
        raise ValueError('원인 분석 상태 오류')
    refs = {x['id']: x for x in item['evidence']}
    if len(refs) != len(item['evidence']):
        raise ValueError('중복 근거')
    for ref in refs.values():
        if not ref.get('quote') or not ref.get('sourceUrl', '').startswith('https://'):
            raise ValueError('원문 근거 누락')
    for metric in item['metrics']:
        if integer(metric['after'])-integer(metric['before']) != integer(metric['delta']):
            raise ValueError('증감액 불일치')
        if metric['components'] and sum(integer(c['impact']) for c in metric['components']) != integer(metric['delta']):
            raise ValueError('기여도 합계 불일치')
        for component in metric['components']:
            if integer(component['after'])-integer(component['before']) != integer(component['delta']):
                raise ValueError('항목 증감액 불일치')
            for ref in component['evidence']:
                if ref not in refs:
                    raise ValueError('잘못된 근거 연결')
        if metric['id']=='fcf':
            if len(metric['components'])!=3:raise ValueError('FCF 구성 항목 누락')
            cfo,ppe,intangibles=metric['components']
            for key in ('before','after'):
                if integer(metric[key])!=integer(cfo[key])-integer(ppe[key])-integer(intangibles[key]):raise ValueError('FCF 정의 불일치')
            if any(integer(c['impact'])!=integer(c['delta'])*sign for c,sign in zip(metric['components'],[1,-1,-1])):raise ValueError('FCF 기여도 부호 오류')
    return item
