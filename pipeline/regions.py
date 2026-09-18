"""Conservative reader for explicit annual geographic tables; no inferred column mapping."""
import re
from .core import parse_amount
from .drivers import revenue_bridge


def extract_regions(blocks, filing, before, after):
    if filing['reportCode']!='11011':return None
    year=filing['year'];candidates=[]
    for b in blocks:
        if b['kind']!='table' or not all(w in b['section'] for w in ['연결','지역','매출']):continue
        headers=[re.sub(r'\s+','',h) for h in b.get('headers',[])]
        def column(y):
            matched=[i for i,h in enumerate(headers) if h in {str(y),str(y)+'년',str(y)+'년누적'}]
            return matched[0] if len(matched)==1 else None
        a,c=column(year-1),column(year)
        if a is None or c is None or a==c:continue
        unit=b.get('unit','');unit_match=re.search(r'단위\s*[:：]\s*(백만원|천원|억원|원)',unit)
        if not unit_match:continue
        multiplier={'원':1,'천원':1000,'백만원':1000000,'억원':100000000}[unit_match[1]]
        parts=[];total=None;valid=True
        for row in b['rows']:
            if len(row)<=max(a,c):valid=False;break
            name=row[0].strip()
            try:old,new=parse_amount(row[a],multiplier),parse_amount(row[c],multiplier)
            except ValueError:valid=False;break
            if name in {'합계','계','총계'}:
                if total is not None:valid=False;break
                total=(old,new)
            else:parts.append(dict(label=name,before=old,after=new,evidence=[b['id']]))
        if not valid or len(parts)<2 or total!=(before,after):continue
        if sum(int(p['before']) for p in parts)!=int(before) or sum(int(p['after']) for p in parts)!=int(after):continue
        metric=revenue_bridge(before,after,parts,evidence=[b['id']])
        ref=dict(id=b['id'],quote=b['text'],sourceUrl=filing['url'],section=b['section'],unit=unit_match[1],columns=b['headers'])
        candidates.append((metric,ref))
    return candidates[0] if len(candidates)==1 else None
