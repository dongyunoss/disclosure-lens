"""Transparent research screening, not a security rating or a causal model.

Inputs are same-filing annual comparative figures in exact KRW. Missing inputs
and undefined ratios produce unavailable rules, never a reassuring result.
"""
from decimal import Decimal, ROUND_HALF_UP
from .core import digest

VERSION = 'review-rules-1'


def screen(facts):
    f = {x['id']: x for x in facts}
    if len(f) != len(facts):
        raise ValueError('중복 재무 항목')
    for x in facts:
        for side in ('before', 'after'):
            if not isinstance(x[side], str) or str(int(x[side])) != x[side]:
                raise ValueError('원 단위 정수 금액만 허용합니다.')
            if x['id'] in {'ppe','intangibles','dividends','buybacks'} and int(x[side])<0:
                raise ValueError('현금유출은 양의 지출 규모로 입력해야 합니다.')
    def v(key, side='after'): return Decimal(f[key][side])
    def ratio(n, d):
        if d <= 0: raise ArithmeticError('분모가 0 또는 음수여서 비율을 계산하지 않습니다.')
        return n / d
    def growth(key): return (ratio(v(key), v(key, 'before')) - 1) * 100
    def fmt(n): return str(n.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    def stat(label, number, unit='%'): return dict(label=label, value=fmt(number), unit=unit)
    def pct(key): return stat(f[key]['label']+' 증감률', growth(key))
    results=[]
    def run(ident, category, title, keys, criterion, why, check, caveat, calc):
        item=dict(id=ident, category=category, title=title, factIds=[k for k in keys if k in f],
                  criterion=criterion, why=why, nextCheck=check, caveat=caveat, stats=[])
        missing=[k for k in keys if k not in f]
        if missing:
            item.update(status='unavailable', unavailableReason='필수 재무 항목 미확보: '+', '.join(missing))
        else:
            try:
                status, stats=calc(); item.update(status=status, stats=stats)
            except ArithmeticError as e:
                item.update(status='unavailable', unavailableReason=str(e))
        results.append(item)
    def margin():
        before=ratio(v('operating','before'),v('revenue','before'))*100
        after=ratio(v('operating'),v('revenue'))*100
        diff=after-before
        return ('attention' if v('operating')<=0 or diff<=-2 else 'movement' if diff>=2 else 'not_triggered',
                [stat('이전 영업이익률',before),stat('이후 영업이익률',after),stat('영업이익률 변화',diff,'%p')])
    run('margin','수익성','매출 증가가 이익률 개선으로 이어졌는가', ['revenue','operating'],
        '영업이익 ÷ 매출 × 100. 영업이익이 0 이하이거나 전년 대비 2%p 이상 하락하면 확인 우선. 그 외 2%p 이상 상승은 주요 변화.',
        '외형 성장과 이익을 남기는 능력을 함께 보면 성장의 질을 검토할 수 있습니다.',
        '제품·사업부 구성, 가격·물량, 원가율과 일회성 비용을 주석·사업부 설명에서 확인하세요.',
        '이익률 상승만으로 지속 가능한 성장을 단정할 수 없습니다. 업종 평균은 반영하지 않았습니다.', margin)
    for key,title in [('receivables','매출채권이 매출보다 빠르게 늘었는가'),('inventory','재고가 매출보다 빠르게 쌓였는가')]:
        run(key,'운전자본',title,[key,'revenue'],
            '해당 자산 증가율 − 매출 증가율 ≥ 5%p이면 확인 우선.',
            '매출 성장보다 더 많은 자금이 영업 자산에 묶이는지 살펴보는 신호입니다.',
            '매출채권 연령·대손충당금·회수 조건을 확인하세요.' if key=='receivables' else '재고 구성·평가손실·회전 기간·수요 전망을 확인하세요.',
            '기말 잔액과 연간 매출의 비교입니다. 회수 지연이나 과잉 재고의 확정 증거가 아니며 환율·인수 영향도 확인해야 합니다.',
            lambda key=key: ('attention' if growth(key)-growth('revenue')>=5 else 'not_triggered',
                             [pct(key),pct('revenue'),stat('증가율 격차',growth(key)-growth('revenue'),'%p')]))
    def cash_quality():
        if v('cfo')<0:
            return ('attention',[stat('영업현금흐름',v('cfo')/100000000,'억 원')])
        return ('attention' if ratio(v('cfo'),v('net_income'))<1 else 'not_triggered',
                [stat('이전 현금 / 이익',ratio(v('cfo','before'),v('net_income','before')),'배'),stat('이후 현금 / 이익',ratio(v('cfo'),v('net_income')),'배')])
    run('cash-quality','현금 창출','회계상 이익이 영업현금으로 이어졌는가',['cfo','net_income'],
        '영업현금흐름이 음수이거나 영업현금흐름 ÷ 당기순이익 < 1배이면 확인 우선. 순이익이 0 이하이면 비율 판단은 보류.',
        '이익과 실제 현금 유입의 간격은 발생주의 항목과 운전자본을 살펴볼 출발점입니다.',
        '비현금 손익, 감가상각, 매출채권·재고·매입채무의 변동을 함께 확인하세요.',
        '1배 이상이어도 이익의 질이 보장되지는 않습니다. 설비 집약 업종에서는 감가상각 영향이 큽니다.',
        cash_quality)
    run('working-capital','현금 창출','운전자본이 현금을 얼마나 흡수했는가',['working_capital','cfo'],
        '운전자본 현금효과의 악화액 ÷ 전기 영업현금흐름 ≥ 10%이면 확인 우선.',
        '영업현금흐름 총액이 늘어도 자산·부채 변동으로 추가 유출된 현금은 별도로 볼 필요가 있습니다.',
        '현금흐름 주석의 매출채권·재고·매입채무별 조정 내역에서 어떤 항목이 현금을 흡수했는지 확인하세요.',
        '합계의 악화 원인을 특정 자산 하나로 단정하지 않습니다. 재무상태표 증감과 현금효과는 일치하지 않을 수 있습니다.',
        lambda: ('attention' if ratio(v('working_capital','before')-v('working_capital'),v('cfo','before'))>=Decimal('.1') else 'not_triggered',
                 [stat('악화액 / 전기 영업현금',ratio(v('working_capital','before')-v('working_capital'),v('cfo','before'))*100)]))
    run('liquidity','재무 여력','단기 지급 의무를 감당할 자산이 있는가',['current_assets','current_liabilities','cash','short_investments'],
        '유동자산 ÷ 유동부채 < 1배이면 확인 우선.',
        '단기 부채와 유동자산의 규모를 비교해 지급 여력 점검의 출발점으로 삼습니다.',
        '현금의 사용 제한, 금융상품 만기, 매출채권 회수 가능성과 차입금 만기를 확인하세요.',
        '유동자산 전부를 현금처럼 사용할 수 있는 것은 아닙니다. 단기금융상품도 사용 제한 여부를 확인해야 합니다.',
        lambda: ('attention' if ratio(v('current_assets'),v('current_liabilities'))<1 else 'not_triggered',
                 [stat('이전 유동비율',ratio(v('current_assets','before'),v('current_liabilities','before')),'배'),stat('이후 유동비율',ratio(v('current_assets'),v('current_liabilities')),'배')]))
    run('short-debt','재무 여력','단기차입금 증가의 용도와 만기는 무엇인가',['short_debt','cash','current_debt','long_debt'],
        '단기차입금 증가율 ≥ 20%이면 확인 우선.',
        '빠르게 늘어난 단기차입은 자금 조달 목적과 차환 계획을 확인할 이유가 됩니다.',
        '차입 통화·금리·만기와 신규 투자 또는 운전자본 수요를 확인하세요. 현금 보유액도 함께 읽으세요.',
        '차입금 증가 자체가 유동성 위기를 뜻하지 않습니다. 단기차입금은 유동성장기부채와 구분합니다.',
        lambda: ('attention' if growth('short_debt')>=20 else 'not_triggered',[pct('short_debt'),pct('cash')]))
    run('investment','자본 배분','영업현금으로 자산 취득 지출을 감당했는가',['cfo','ppe','intangibles'],
        '(유형자산 취득 지출 + 무형자산 취득 지출) ÷ 영업현금흐름 > 100%이면 확인 우선.',
        '영업현금의 어느 정도가 자산 취득에 쓰이는지 보면 추가 자금 조달 필요성을 검토할 수 있습니다.',
        '유지·성장 투자 비중, 투자 계획과 향후 현금 창출 시점을 확인하세요.',
        '취득 지출은 양의 규모로 계산합니다. 이 FCF 정의에는 기업 인수와 금융상품 투자를 포함하지 않습니다.',
        lambda: ('attention' if ratio(v('ppe')+v('intangibles'),v('cfo'))>1 else 'not_triggered',
                 [stat('취득 지출 / 영업현금',ratio(v('ppe')+v('intangibles'),v('cfo'))*100),stat('FCF', (v('cfo')-v('ppe')-v('intangibles'))/100000000,'억 원')]))
    run('intangible','자본 배분','무형자산 증가의 성격은 무엇인가',['intangible_assets','assets','intangibles'],
        '무형자산 장부금액 증가율 ≥ 20%이고 총자산 비중 ≥ 3%이면 주요 변화.',
        '무형자산이 커지면 자산의 구성과 회수 가능성을 함께 살펴볼 필요가 있습니다.',
        '영업권·개발비·취득 자산의 구성, 상각 기간과 손상검사 가정을 확인하세요.',
        '장부금액 증가는 현금 취득과 같지 않습니다. 인수·환율 등 비현금 변동도 포함될 수 있습니다.',
        lambda: ('movement' if growth('intangible_assets')>=20 and ratio(v('intangible_assets'),v('assets'))>=Decimal('.03') else 'not_triggered',
                 [pct('intangible_assets'),stat('총자산 중 비중',ratio(v('intangible_assets'),v('assets'))*100)]))
    run('payout','자본 배분','배당·자사주 지출과 현금 창출의 균형은 어떠한가',['dividends','buybacks','cfo','ppe','intangibles'],
        '배당·자사주 지출이 양수이고 FCF를 초과하면 확인 우선. 아니면 자사주 취득 증가율 ≥ 50%는 주요 변화.',
        '투자 후 남은 현금과 주주환원 지출을 비교하면 자본 배분 정책을 검토할 수 있습니다.',
        '주주환원 정책, 자기주식 소각·처분 계획과 향후 투자·차입 계획을 확인하세요.',
        '특정 연도 지출만으로 정책의 지속 가능성을 단정하지 않습니다. 자사주 취득과 소각은 다릅니다.',
        lambda: ('attention' if v('dividends')+v('buybacks')>max(Decimal(0),v('cfo')-v('ppe')-v('intangibles')) else 'movement' if v('buybacks','before')>0 and growth('buybacks')>=50 else 'not_triggered',
                 [stat('배당·자사주 지출',(v('dividends')+v('buybacks'))/100000000,'억 원'),stat('FCF',(v('cfo')-v('ppe')-v('intangibles'))/100000000,'억 원')]))
    return results


def validate_review(data, root=None):
    from .table_overlays import validate_overlays
    if data['schemaVersion']!=1 or data['ruleVersion']!=VERSION or data['basis']!='연결' or data['currency']!='KRW' or data['periodType']!='annual':
        raise ValueError('검토 기준 불일치')
    if data['findings']!=screen(data['facts']): raise ValueError('검토 결과 재계산 불일치')
    ids={x['id'] for x in data['facts']}
    covered=set()
    for table in data['tables']:
        facts=[x for x in data['facts'] if x['tableId']==table['id']]
        if not facts: raise ValueError('근거 없는 표')
        metrics=[dict(id=table['metricId'],components=[dict(label=f['label'],before=f['before'],after=f['after']) for f in facts])]
        validate_overlays(dict(source=data['source'],metrics=metrics,tableOverlays=[table]))
        covered.update(f['id'] for f in facts)
        if root:
            path=(root/'public'/table['asset']).resolve()
            if not path.is_relative_to((root/'public/drivers/tables').resolve()) or digest(path.read_bytes())!=table['assetSha256']:
                raise ValueError('표 이미지 무결성 오류')
    if covered!=ids: raise ValueError('재무 항목의 원문 표 누락')
    return data
