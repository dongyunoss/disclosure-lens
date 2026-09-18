"""Extract and verify annual research facts and original table cells from retained PDF."""
import io
import re
from pathlib import Path
from .core import load, save, digest, now, parse_amount
from .investment_review import VERSION, screen, validate_review
from .table_overlays import normalized_rect

# Exact row anchors, not manually transcribed financial values.
ROWS = {
    83: [('current_assets','유동자산'),('cash','현금및현금성자산'),('short_investments','단기금융상품'),
         ('receivables','매출채권'),('inventory','재고자산'),('intangible_assets','무형자산'),('assets','자산총계'),
         ('current_liabilities','유동부채'),('short_debt','단기차입금')],
    84: [('current_debt','유동성장기부채'),('long_debt','장기차입금')],
    85: [('revenue','매출액'),('operating','영업이익'),('net_income','당기순이익')],
    89: [('cfo','영업활동현금흐름'),('working_capital','영업활동으로 인한 자산부채의 변동'),
         ('ppe','유형자산의 취득'),('intangibles','무형자산의 취득')],
    90: [('dividends','배당금의 지급'),('buybacks','자기주식의 취득')],
}
CROPS={83:(47,108,548,799),84:(47,47,548,485),85:(47,90,548,552),89:(47,90,548,802),90:(47,47,548,197)}
OUTFLOWS={'ppe','intangibles','dividends','buybacks'}


def build(root):
    import pdfplumber
    from pypdf import PdfReader
    source=load(root/'public/drivers/samsung-2025-drivers-v1.json')['source']
    path=root/'private/official-pdf/samsung-2025.pdf'
    if digest(path.read_bytes())!=source['sha256']: raise ValueError('원본 해시 불일치')
    reader=PdfReader(path)
    for page,title in [(83,'연결 재무상태표'),(85,'연결 손익계산서'),(89,'연결 현금흐름표')]:
        content=reader.pages[page-1].extract_text()
        if not all(s in content for s in [title,'백만원','2025','2024']): raise ValueError('연결·기간·단위 검증 실패')
    facts=[];tables=[]
    with pdfplumber.open(path) as pdf:
        for page_num, rows in ROWS.items():
            page=pdf.pages[page_num-1];crop=CROPS[page_num];table_id='review-'+str(page_num)
            marks=[];text=reader.pages[page_num-1].extract_text();words=page.extract_words()
            title='연결 재무상태표' if page_num in (83,84) else '연결 손익계산서' if page_num==85 else '연결 현금흐름표'
            for ident,label in rows:
                lines=[line.strip() for line in text.splitlines() if re.match(re.escape(label)+r'(?:\s|$)',line.strip())]
                if len(lines)!=1: raise ValueError('행 식별 실패: '+label)
                match=re.search(r'(\(?[\d,]+\)?)\s+(\(?[\d,]+\)?)\s+(\(?[\d,]+\)?)\s*$',lines[0])
                if not match: raise ValueError('3개 비교열 식별 실패: '+label)
                values={};outflow=ident in OUTFLOWS
                for side,raw in [('after',match[1]),('before',match[2])]:
                    amount=int(parse_amount(raw,1000000))
                    if outflow and amount>0: raise ValueError('현금유출 부호 검수 필요')
                    values[side]=str(abs(amount) if outflow else amount)
                    matches=[w for w in words if w['text']==raw and crop[0]<=w['x0'] and w['x1']<=crop[2] and crop[1]<=w['top'] and w['bottom']<=crop[3]]
                    if len(matches)!=1: raise ValueError('금액 위치가 모호합니다: '+label+' '+raw)
                    w=matches[0];x=(w['x0']+w['x1'])/2;y=(w['top']+w['bottom'])/2
                    cells={tuple(c) for t in page.find_tables() for row in t.rows for c in row.cells if c and c[0]<=x<=c[2] and c[1]<=y<=c[3]}
                    if len(cells)!=1: raise ValueError('셀 위치 검증 실패: '+label)
                    marks.append(dict(partLabel=label,side=side,rawValue=raw,cashOutflow=outflow,rect=normalized_rect(cells.pop(),crop)))
                facts.append(dict(id=ident,label=label,**values,tableId=table_id,quote=lines[0],
                                  kind='instant' if page_num in (83,84) else 'duration',cashOutflow=outflow))
            image=page.crop(crop).to_image(resolution=160,antialias=True).original.convert('RGB')
            buffer=io.BytesIO();image.save(buffer,format='PNG');raw=buffer.getvalue();sha=digest(raw)
            asset=f'drivers/tables/samsung-2025-review-{page_num}-{sha[:12]}.png'
            (root/'public'/asset).write_bytes(raw)
            tables.append(dict(id=table_id,metricId=table_id,title=title+(' (계속)' if page_num in (84,90) else ''),
                               asset=asset,assetSha256=sha,sourceSha256=source['sha256'],sourceUrl=source['url']+'#page='+str(page_num),
                               page=page_num,printedPage=page_num-3,width=image.width,height=image.height,unit='백만원',highlights=marks))
    data=dict(schemaVersion=1,ruleVersion=VERSION,id='samsung-2025-review-v1',companyId='samsung',companyName='삼성전자',
              basis='연결',currency='KRW',periodType='annual',beforeYear=2024,afterYear=2025,source=source,generatedAt=now(),
              facts=facts,tables=tables,findings=screen(facts),
              coverageGaps=['주석의 대손충당금·재고평가손실·손상차손 상세', '차입금 만기·금리·약정 및 현금 사용 제한',
                            '우발채무·소송·특수관계자 거래', '사업부·지역별 원인 설명과 일회성 손익', '업종·경쟁사 비교, 주가·밸류에이션'])
    validate_review(data,root)
    save(root/'public/review/samsung-2025-review-v1.json',data)
    save(root/'public/review/catalog.json',dict(schemaVersion=1,items=[dict(id=data['id'],companyId='samsung',path='review/'+data['id']+'.json')]))
    return data


if __name__=='__main__':
    build(Path(__file__).resolve().parents[1])
    print('Investment review and source cells generated.')
