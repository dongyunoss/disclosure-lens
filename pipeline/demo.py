"""Deliberately fictional fixtures. Never publish these as reviewed filings."""
import json
from pathlib import Path

COMPANIES = [('samsung','삼성전자','005930'),('skhynix','SK하이닉스','000660'),('lge','LG전자','066570')]

def generate(root: Path):
    target=root/'public'/'demo'; target.mkdir(parents=True,exist_ok=True)
    catalog={'schemaVersion':1,'companies':[]}
    for index,(cid,name,stock) in enumerate(COMPANIES):
        reports=[dict(id=f'demo-{cid}-{y}',companyId=cid,year=y,receipt=None,filedAt=None,corrected=False,checkedAt=None,sha256='DEMO-NOT-A-FILING',dartUrl=None) for y in [2024,2025]]
        evidence=[];changes=[]
        def block(side, suffix, text,section='II. 사업의 내용 > 1. 사업의 개요'):
            b=dict(id=f'{reports[side]["id"]}-{suffix}',reportId=reports[side]['id'],kind='paragraph',section=section,order=len(evidence),text=text,normalized=' '.join(text.split()),contextBefore='[가상 예시] 이 문단은 화면 기능을 설명하기 위해 작성되었습니다.',contextAfter='표시된 내용은 실제 기업의 공시나 사업 현황을 나타내지 않습니다.')
            evidence.append(b);return dict(blockId=b['id'],quote=text)
        specs=[
          ('content','제품 설명의 범위 확대','제품 소개 문장에 기업용 제품이 함께 기재되었습니다. 실제 사업 개시 여부는 이 예시로 판단할 수 없습니다.','당사는 소비자용 전자 제품을 공급하고 있습니다.','당사는 소비자용 전자 제품과 기업용 솔루션을 공급하고 있습니다.'),
          ('added','서비스 설명 문단 추가','이후 문서의 주요 제품·서비스 절에 유지보수 서비스 설명이 추가되었습니다.',None,'제품 공급과 함께 정기 점검 및 유지보수 서비스를 설명하고 있습니다.'),
          ('removed','유통 경로 설명 삭제','이전 문서에 있던 유통 경로 문장이 이후 문서의 분석 대상 절에서 확인되지 않습니다.','제품은 지역별 유통 협력사를 통해 공급됩니다.',None),
          ('content','연구개발 설명 변경','연구개발 대상으로 기재된 문구에 사용 편의성이 추가되었습니다.','연구개발은 제품 성능 개선에 집중하고 있습니다.','연구개발은 제품 성능과 사용 편의성 개선에 집중하고 있습니다.'),
          ('wording','공급 지역 표현 정리','동일한 공급 지역을 다르게 표현한 예시입니다.','제품을 국내 및 해외 시장에 공급합니다.','제품을 국내외 시장에 공급합니다.')]
        for i,(kind,title,explanation,before,after) in enumerate(specs):
            section='사업 개요' if i in [0,3,4] else '주요 제품·서비스'
            path='II. 사업의 내용 > '+section
            changes.append(dict(id=f'change-{i+1}',kind=kind,section=section,title=title,explanation=explanation,before=[block(0,str(i),before,path)] if before else [],after=[block(1,str(i),after,path)] if after else [],reviewStatus='needs_review'))
        financials=[]
        for i,(label,before,after) in enumerate([('매출',10000000000000*(index+1),11800000000000*(index+1)),('영업이익',-100000000000 if index==1 else 1000000000000,400000000000 if index==1 else 1260000000000)]):
            ids=[]
            for side,val in enumerate([before,after]):
                text=f'{label} | {val:,}'; citation=block(side,f'finance-{i}',text,'III. 재무에 관한 사항 > 연결손익계산서')
                evidence[-1].update(kind='table',headers=['계정','당기금액 (원)'],rows=[[label,f'{val:,}']],unit='가상 예시 · 단위: 원 · 연결 기준');ids.append(citation['blockId'])
            financials.append(dict(id=f'financial-{i}',label=label,before=str(before),after=str(after),delta=str(after-before),percent=f'{(after-before)/before*100:.2f}' if before>0 else None,status='흑자 전환' if before<0<after else '증가',reason=None,beforeBlockId=ids[0],afterBlockId=ids[1],currency='KRW',basis='CFS',beforeRow=0,afterRow=0))
        pair=f'{cid}-2024-2025-demo'
        data=dict(schemaVersion=1,id=pair,companyId=cid,companyName=name,stockCode=stock,mode='demo',version='demo-v1',checkedAt=None,reports=reports,financials=financials,changes=changes,evidence=evidence,analysis=dict(model='none-fictional-fixture',promptVersion='demo-v1'),coverage=['연결 매출','연결 영업이익','사업 개요','주요 제품·서비스'])
        (target/f'{pair}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        catalog['companies'].append(dict(id=cid,name=name,stockCode=stock,comparisons=[dict(id=pair,years=[2024,2025],path=f'demo/{pair}.json',mode='demo')]))
    (target/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    generate(Path(__file__).resolve().parents[1])
