"""Extract selected passages from official IR PDFs without an API key.

Original PDFs remain private. Public output contains only short selected passages,
factual financial rows, and their document/page provenance.
"""
import argparse
import re
import urllib.parse
import urllib.request
from pathlib import Path
from .core import digest, load, now, save

HOSTS={'images.samsung.com','www.lge.co.kr'}

def extract_passage(text,start,end):
    a=text.find(start)
    b=text.find(end,a) if a>=0 else -1
    if a<0 or b<0:raise ValueError('지정한 발췌문을 원문에서 찾지 못했습니다.')
    return text[a:b+len(end)]

def extract_row(text,label):
    matches=[line.strip() for line in text.splitlines() if line.strip().startswith(label)]
    if len(matches)!=1:raise ValueError('재무표 행을 유일하게 식별하지 못했습니다.')
    quote=matches[0]
    values=re.findall(r'(?<!\w)\(?-?\d{1,3}(?:,\d{3})+\)?',quote)
    if len(values)!=3:raise ValueError('당기·전기·전전기 세 금액을 확인하지 못했습니다.')
    return quote,values

def validate_library(library):
    if library.get('schemaVersion')!=1:raise ValueError('발췌 데이터 계약 오류')
    ids=set()
    for source in library['sources']:
        parsed=urllib.parse.urlparse(source['url'])
        if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.username or parsed.password:raise ValueError('공식 PDF 출처가 아닙니다.')
        if not re.fullmatch(r'[0-9a-f]{64}',source['sha256']):raise ValueError('원본 해시 누락')
        if source['id'] in ids:raise ValueError('중복 출처 ID')
        ids.add(source['id'])
        if source['latestCorrectionVerified'] is not False:raise ValueError('정정 여부를 자동 확인한 것으로 표시할 수 없습니다.')
        total=0;item_ids=set()
        for item in source['excerpts']:
            if item['id'] in item_ids or not item['quote'].strip():raise ValueError('중복 ID 또는 빈 발췌문')
            item_ids.add(item['id'])
            if not isinstance(item['page'],int) or not 1<=item['page']<=source['pageCount']:raise ValueError('잘못된 PDF 페이지')
            if item['kind']=='paragraph':total+=len(item['quote'].split())
            elif item['kind']=='table':
                if len(item['values'])!=3 or item['unit']!='백만원' or item['basis']!='연결':raise ValueError('재무표 메타데이터 오류')
                if not all(value in item['quote'] for value in item['values']):raise ValueError('금액이 발췌한 행과 다릅니다.')
            else:raise ValueError('알 수 없는 발췌 유형')
        if total>25:raise ValueError('공개 미리보기에는 보고서당 25단어 이내의 짧은 인용문만 포함하세요.')

def build(root,refresh=False):
    from pypdf import PdfReader
    config=load(root/'config'/'excerpts.json');sources=[]
    for spec in config['sources']:
        url=spec['url'];parsed=urllib.parse.urlparse(url)
        if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.username or parsed.password:raise ValueError('허용되지 않은 원문 주소')
        path=root/'private'/'official-pdf'/(spec['id']+'.pdf')
        if refresh or not path.exists():
            with urllib.request.urlopen(url,timeout=45) as response:
                if urllib.parse.urlparse(response.url).hostname not in HOSTS:raise ValueError('원문 주소가 다른 도메인으로 이동했습니다.')
                raw=response.read(25_000_001)
            if len(raw)>25_000_000 or not raw.startswith(b'%PDF'):raise ValueError('지원하지 않는 PDF 파일')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        raw=path.read_bytes();reader=PdfReader(path)
        pages={number:reader.pages[number-1].extract_text() for number in {spec[k] for k in ['coverPage','paragraphPage','statementPage','revenuePage','profitPage']}}
        cover=pages[spec['coverPage']]
        if spec['companyName'] not in re.sub(r'\s+','',cover) or str(spec['year'])+'년 01월 01일' not in cover:raise ValueError('보고서 회사·회계연도가 다릅니다.')
        date=re.search(r'귀중\s*(\d{4})년\s*(\d+)월\s*(\d+)일',cover)
        if not date:raise ValueError('보고서 제출일을 확인하지 못했습니다.')
        filed='-'.join([date[1],date[2].zfill(2),date[3].zfill(2)])
        statement=pages[spec['statementPage']]
        if '연결 손익계산서' not in statement or not re.search(r'단위\s*:\s*백만원',statement):raise ValueError('연결 손익계산서 또는 단위를 확인하지 못했습니다.')
        if f"{spec['year']}.01.01" not in statement or f"{spec['year']}.12.31" not in statement:raise ValueError('연간 회계기간이 일치하지 않습니다.')
        def page_label(number):
            m=re.search(r'dart\.fss\.or\.kr\s+Page\s+(\d+)',pages[number])
            return m[1] if m else None
        paragraph=extract_passage(pages[spec['paragraphPage']],spec['paragraphStart'],spec['paragraphEnd'])
        items=[dict(id='business',kind='paragraph',title='사업 개요 · 문장 발췌',section='II. 사업의 내용 > 1. 사업의 개요',quote=paragraph,page=spec['paragraphPage'],printedPage=page_label(spec['paragraphPage']))]
        for key,label in [('revenue','매출액'),('profit','영업이익')]:
            number=spec[key+'Page'];quote,values=extract_row(pages[number],label)
            items.append(dict(id=key,kind='table',title=label+' · 원문 표 행',section='III. 재무에 관한 사항 > 연결 손익계산서',quote=quote,page=number,printedPage=page_label(number),values=values,headers=[str(spec['year']-i) for i in range(3)],unit='백만원',basis='연결',statementPage=spec['statementPage']))
        sources.append(dict(id=spec['id'],companyId=spec['companyId'],companyName=spec['companyName'],year=spec['year'],url=url,listingUrl=spec['listingUrl'],filedAt=filed,retrievedAt=now(),sha256=digest(raw),pageCount=len(reader.pages),latestCorrectionVerified=False,excerpts=items))
    library=dict(schemaVersion=1,sources=sources,unavailable=[dict(companyId='skhynix',companyName='SK하이닉스',reason='공식 사업보고서 PDF 연결 준비 중')])
    validate_library(library)
    save(root/'public'/'excerpts'/'library.json',library)
    return library

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='기업 공식 사업보고서에서 출처를 포함한 짧은 발췌 생성')
    parser.add_argument('--refresh',action='store_true');args=parser.parse_args()
    result=build(Path(__file__).resolve().parents[1],args.refresh)
    print(f"{len(result['sources'])}개 실제 사업보고서의 발췌 생성 완료")
