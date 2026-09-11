"""Network access is restricted to official OpenDART endpoints; secrets never enter logs."""
import io
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from defusedxml import ElementTree as ET
from .core import COMPANIES, digest, load, now, save

class DartError(RuntimeError):pass

class DartClient:
    def __init__(self,key=None):
        self.key=key or os.getenv('DART_API_KEY')
        if not self.key:raise DartError('DART_API_KEY를 비공개 .env에 설정하세요.')
    def request(self,endpoint,**params):
        url='https://opendart.fss.or.kr/api/'+endpoint+'?'+urllib.parse.urlencode(dict(crtfc_key=self.key,**params))
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url,timeout=45) as res:
                    raw=res.read(100_000_001)
                if len(raw)>100_000_000:raise DartError('파일 크기 한도 초과')
                if endpoint.endswith('.json'):
                    import json
                    obj=json.loads(raw)
                    if obj.get('status')!='000':raise DartError(f'OpenDART 응답 코드 {obj.get("status","unknown")}')
                    return obj
                if not raw.startswith(b'PK'):
                    try:code=ET.fromstring(raw).findtext('status')
                    except Exception:code='invalid'
                    raise DartError(f'OpenDART 파일 응답 코드 {code}')
                return raw
            except (urllib.error.URLError,TimeoutError):
                if attempt==2:raise DartError('OpenDART 연결 실패. 기존 공개본을 유지합니다.') from None
                time.sleep(attempt+1)
        raise DartError('OpenDART 요청 실패')

def xml_members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members=archive.infolist()
        if sum(i.file_size for i in members)>250_000_000:raise DartError('압축 해제 크기 한도 초과')
        for info in members:
            if info.filename.lower().endswith('.xml'):
                yield info.filename,archive.read(info)

def corporation_codes(client):
    _,raw=next(xml_members(client.request('corpCode.xml')))
    root=ET.fromstring(raw);by_stock={item.findtext('stock_code','').strip():item.findtext('corp_code') for item in root.findall('list')}
    return {cid:by_stock[stock] for cid,(_,stock) in COMPANIES.items()}

def discover(client,corp_code):
    reports=[];page=1
    while True:
        try:result=client.request('list.json',corp_code=corp_code,bgn_de='20250101',end_de=date.today().strftime('%Y%m%d'),pblntf_detail_ty='A001',last_reprt_at='Y',page_count=100,page_no=page)
        except DartError as exc:
            if '013' in str(exc):break
            raise
        reports.extend(result['list'])
        if page>=int(result['total_page']):break
        page+=1
    selected={}
    for year in [2024,2025]:
        rows=[r for r in reports if re.search(rf'사업보고서\s*\({year}\.12\)',r['report_nm']) and '철' not in r.get('rm','')]
        if not rows:raise DartError(f'{year} 사업보고서 최종본을 찾지 못했습니다.')
        selected[year]=max(rows,key=lambda r:r['rcept_no'])
    return selected

def collect(root,company_ids=None):
    client=DartClient();codes=corporation_codes(client);result=[]
    for cid in company_ids or COMPANIES:
        selected=discover(client,codes[cid])
        for year,item in selected.items():
            receipt=item['rcept_no'];folder=root/'private'/'raw'/cid/receipt
            checked=now()
            if (folder/'source.zip').exists():
                raw=(folder/'source.zip').read_bytes()
            else:
                raw=client.request('document.xml',rcept_no=receipt)
                folder.mkdir(parents=True,exist_ok=True);(folder/'source.zip').write_bytes(raw)
            report=dict(id=f'{cid}-{receipt}',companyId=cid,year=year,receipt=receipt,filedAt=item['rcept_dt'][:4]+'-'+item['rcept_dt'][4:6]+'-'+item['rcept_dt'][6:],corrected='정정' in item['report_nm'],checkedAt=checked,sha256=digest(raw),dartUrl=f'https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt}')
            accounts=client.request('fnlttSinglAcnt.json',corp_code=codes[cid],bsns_year=year,reprt_code='11011')['list']
            snapshot=folder/'snapshots'/checked.replace(':','-')
            save(snapshot/'accounts.json',accounts);save(snapshot/'report.json',report);save(snapshot/'search.json',item)
            save(folder/'current.json',dict(snapshot=str(snapshot.relative_to(root)),receipt=receipt,checkedAt=checked))
            result.append(dict(companyId=cid,year=year,receipt=receipt,path=str(folder.relative_to(root)),snapshot=str(snapshot.relative_to(root))))
    save(root/'private'/'collection.json',result)
    return result
