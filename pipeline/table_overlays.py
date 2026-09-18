"""Render original PDF tables and bind highlights to verified PDF cells."""
from pathlib import Path
from .core import digest, parse_amount


def normalized_rect(cell, crop):
    x0,y0,x1,y1=cell;left,top,right,bottom=crop
    if not (left<=x0<x1<=right and top<=y0<y1<=bottom):
        raise ValueError('강조 셀이 원문 표 이미지 밖에 있습니다.')
    return dict(x=(x0-left)/(right-left),y=(y0-top)/(bottom-top),
                width=(x1-x0)/(right-left),height=(y1-y0)/(bottom-top))


def validate_overlays(analysis):
    metrics={m['id']:m for m in analysis['metrics']}
    for table in analysis.get('tableOverlays',[]):
        if table['sourceSha256']!=analysis['source']['sha256'] or table['metricId'] not in metrics:
            raise ValueError('원본 표와 분석 보고서가 다릅니다.')
        if table['unit']!='백만원' or table['sourceUrl']!=analysis['source']['url']+'#page='+str(table['page']):
            raise ValueError('원문 표의 단위 또는 페이지 연결 오류')
        if not table['asset'].startswith('drivers/tables/') or '..' in table['asset']:
            raise ValueError('잘못된 표 이미지 경로')
        if table['page']<1 or min(table['width'],table['height'])<1:
            raise ValueError('표 이미지 크기 또는 페이지 오류')
        parts={p['label']:p for p in metrics[table['metricId']]['components']}
        seen=set()
        for mark in table['highlights']:
            rect=mark['rect'];label,side=mark['partLabel'],mark['side']
            if label not in parts or side not in ('before','after') or (label,side) in seen:
                raise ValueError('중복 또는 알 수 없는 강조 셀')
            seen.add((label,side))
            if not(0<=rect['x']<1 and 0<=rect['y']<1 and rect['width']>0 and rect['height']>0 and rect['x']+rect['width']<=1.000001 and rect['y']+rect['height']<=1.000001):
                raise ValueError('강조 좌표 범위 오류')
            value=int(parse_amount(mark['rawValue'],1000000))
            if mark['cashOutflow']:value=abs(value)
            if str(value)!=parts[label][side]:raise ValueError('원문 셀의 값이 분석 수치와 다릅니다.')
        if seen!={(label,side) for label in parts for side in ('before','after')}:
            raise ValueError('비교 금액의 원문 강조 위치가 누락되었습니다.')


def attach(root, analysis):
    import pdfplumber
    pdf_path=root/'private/official-pdf/samsung-2025.pdf'
    if digest(pdf_path.read_bytes())!=analysis['source']['sha256']:
        raise ValueError('강조 위치를 연결할 원본의 해시가 다릅니다.')
    specifications=[('fcf',89,(47,50,548,640)),('revenue',185,(47,390,548,624))]
    overlays=[]
    with pdfplumber.open(pdf_path) as pdf:
        for metric_id,number,crop in specifications:
            page=pdf.pages[number-1];words=page.extract_words();tables=page.find_tables()
            metric=next(m for m in analysis['metrics'] if m['id']==metric_id)
            marks=[]
            for part in metric['components']:
                outflow=metric_id=='fcf' and part['label']!='영업현금흐름 변화'
                for side in ('before','after'):
                    amount=int(part[side])
                    if amount%1000000:raise ValueError('백만원 단위 원문과 정확히 대응하지 않습니다.')
                    raw=f'{amount//1000000:,}'
                    if outflow and amount:raw='('+raw+')'
                    matched=[w for w in words if w['text']==raw and crop[0]<=w['x0'] and w['x1']<=crop[2] and crop[1]<=w['top'] and w['bottom']<=crop[3]]
                    if len(matched)!=1:raise ValueError('원문 숫자의 위치가 모호합니다. 좌표 매핑을 검수하세요.')
                    word=matched[0];cx=(word['x0']+word['x1'])/2;cy=(word['top']+word['bottom'])/2
                    cells={tuple(cell) for t in tables for row in t.rows for cell in row.cells if cell and cell[0]<=cx<=cell[2] and cell[1]<=cy<=cell[3]}
                    if len(cells)!=1:raise ValueError('원문 숫자가 속한 셀을 유일하게 찾지 못했습니다.')
                    marks.append(dict(partLabel=part['label'],side=side,rawValue=raw,cashOutflow=outflow,rect=normalized_rect(next(iter(cells)),crop)))
            image=page.crop(crop).to_image(resolution=160,antialias=True).original.convert('RGB')
            target=root/'public/drivers/tables';target.mkdir(parents=True,exist_ok=True)
            # The image is an unannotated original table; all marks stay in a separate UI layer.
            import io
            buffer=io.BytesIO();image.save(buffer,format='PNG');raw_image=buffer.getvalue();sha=digest(raw_image)
            name=f'samsung-2025-{metric_id}-{sha[:12]}.png';(target/name).write_bytes(raw_image)
            overlays.append(dict(id='samsung-2025-'+metric_id,metricId=metric_id,
                title='연결 현금흐름표' if metric_id=='fcf' else '연결 주석 · 순매출액의 지역별 공시',
                asset='drivers/tables/'+name,assetSha256=sha,width=image.width,height=image.height,
                sourceSha256=analysis['source']['sha256'],sourceUrl=analysis['source']['url']+'#page='+str(number),
                page=number,printedPage=number-3,unit='백만원',highlights=marks))
    analysis['tableOverlays']=overlays;validate_overlays(analysis)
    return analysis


if __name__=='__main__':
    from .core import load,save
    root=Path(__file__).resolve().parents[1]
    target=root/'public/drivers/samsung-2025-drivers-v1.json'
    save(target,attach(root,load(target)))
    print('실제 공시 표 이미지와 금액 셀 강조 위치 생성 완료')
