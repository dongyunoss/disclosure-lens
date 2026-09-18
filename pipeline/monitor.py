"""Polling worker: discover -> durable queue -> analyze -> optional static publication.

Run with --watch on an always-on host. This module never claims a push/SLA guarantee.
"""
import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import subprocess
import time
from .core import COMPANIES, load, save, now, digest
from .dart import DartClient, DartError, corporation_codes
from .drivers import validate_analysis
from .live_analysis import analyze

KST=timezone(timedelta(hours=9))


def classify(row, cid, corp_code):
    if '철' in row.get('rm',''):return None
    title=row['report_nm'];compact=re.sub(r'\s+','',title)
    match=re.search(r'(사업|반기|분기)보고서\s*\((\d{4})\.(\d{2})\)',title)
    regular=False;year=month=code=None
    if match:
        year,month=int(match[2]),int(match[3])
        code={('사업',12):'11011',('반기',6):'11012',('분기',3):'11013',('분기',9):'11014'}.get((match[1],month))
        regular=bool(code)
    elif not any(word in compact for word in ['잠정','매출액또는손익구조']):return None
    receipt=row['rcept_no']
    if not re.fullmatch(r'\d{14}',receipt):raise ValueError('잘못된 접수번호')
    return dict(receipt=receipt,companyId=cid,corpCode=corp_code,title=title,year=year,month=month,reportCode=code,
                regular=regular,corrected='정정' in title,filedAt=row['rcept_dt'],
                url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+receipt,
                status='queued' if regular else 'source_pending',attempts=0,nextAttemptAt=0)


def recent(client, code, start, end):
    rows=[];page=1
    while True:
        try:result=client.request('list.json',corp_code=code,bgn_de=start,end_de=end,last_reprt_at='N',page_no=page,page_count=100,sort='date',sort_mth='desc')
        except DartError as exc:
            if str(exc)=='OpenDART 응답 코드 013':return rows
            raise
        rows.extend(result['list'])
        if page>=int(result['total_page']):return rows
        page+=1


def publish(root, result):
    validate_analysis(result)
    version=digest({k:v for k,v in result.items() if k!='generatedAt'})[:16]
    relative='drivers/'+result['id']+'-'+version+'.json'
    save(root/'public'/relative,result)
    path=root/'public/drivers/catalog.json'
    catalog=load(path) if path.exists() else dict(schemaVersion=1,items=[])
    entry={k:result[k] for k in ('id','companyId','companyName','title','status')};entry['path']=relative
    catalog['items']=[entry]+[x for x in catalog['items'] if x['id']!=entry['id']]
    save(path,catalog)


def run_once(root, *, client=None, publish_automatic=False, clock=None, analyzer=analyze):
    moment=clock or datetime.now(KST)
    directory=root/'private/monitor';directory.mkdir(parents=True,exist_ok=True)
    lock=directory/'worker.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise ValueError('다른 감지 작업이 실행 중입니다.') from None
    os.close(fd)
    try:
        path=directory/'state.json'
        state=load(path) if path.exists() else dict(schemaVersion=1,companies={},jobs={},codes={})
        client=client or DartClient()
        if not state['codes']:state['codes']=corporation_codes(client)
        failures=[]
        for cid,code in state['codes'].items():
            end=moment.date()
            last=state['companies'].get(cid)
            start=(datetime.fromisoformat(last).date()-timedelta(days=2)) if last else end-timedelta(days=7)
            try:
                for row in recent(client,code,start.strftime('%Y%m%d'),end.strftime('%Y%m%d')):
                    filing=classify(row,cid,code)
                    if filing and filing['receipt'] not in state['jobs']:
                        filing['detectedAt']=moment.isoformat();state['jobs'][filing['receipt']]=filing
                state['companies'][cid]=moment.isoformat()
            except (DartError,ValueError):failures.append(cid)
        save(path,state)  # Persist the queue before any analysis/network work.
        published=0
        pending=sorted([j for j in state['jobs'].values() if j['status'] in {'queued','retry','partial'} and j['nextAttemptAt']<=moment.timestamp()],key=lambda j:j['receipt'],reverse=True)
        for job in pending[:5]:
            job['attempts']+=1
            try:
                result=analyzer(root,client,job)
                validate_analysis(result)
                if publish_automatic:publish(root,result);published+=1
                job['status']='done' if {m['id'] for m in result['metrics']}=={'fcf','revenue'} else 'partial'
                job['analysisId']=result['id'];job['published']=publish_automatic
                job['message']='자동 산술 분석 완료 · 서술 원인은 검수 필요' if job['status']=='done' else '일부 계정 보류 · 재무 데이터 갱신 대기'
            except (ValueError,DartError,KeyError,IndexError):
                job['status']='retry';job['message']='원문 또는 재무 데이터 확인 대기 · 자동 재시도'
            # Bounded exponential retries, then daily. No duplicate successful jobs.
            delay=min(300*2**min(job['attempts']-1,8),86400)
            job['nextAttemptAt']=moment.timestamp()+delay
            if job['attempts']>=12 and job['status']!='done':
                job['status']='needs_review';job['message']='자동 확인 범위를 벗어나 운영자 검수 필요'
            save(path,state)
        public_jobs=[]
        for j in sorted(state['jobs'].values(),key=lambda x:x['receipt'],reverse=True)[:30]:
            fields={k:j[k] for k in ('receipt','companyId','title','filedAt','url','status','detectedAt')}
            fields['message']=j.get('message','잠정실적 감지 · 현금흐름·자본지출 근거가 없어 정기보고서를 기다립니다.' if not j['regular'] else '분석 대기')
            public_jobs.append(fields)
        status=dict(schemaVersion=1,state='degraded' if failures else 'polling',checkedAt=moment.isoformat(),intervalSeconds=300,
                    message='일부 기업 조회 실패 · 마지막 분석 유지' if failures else '새 공시를 정기 확인 중입니다. 재무 API와 배포 지연이 추가될 수 있습니다.',filings=public_jobs)
        save(root/'public/drivers/monitor.json',status)
        return dict(published=published,failures=failures,queued=len(pending))
    finally:lock.unlink(missing_ok=True)


def main():
    from .cli import env_file
    root=Path(__file__).resolve().parents[1];env_file(root)
    parser=argparse.ArgumentParser(description='신규·정정 공시 감지와 자동 산술 분석')
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--publish-automatic',action='store_true',help='자동 산출·미검수 상태를 명시해 정적 JSON 공개')
    parser.add_argument('--deploy',action='store_true',help='공개 결과를 검증 후 기존 GitHub Pages에 배포')
    args=parser.parse_args()
    if args.deploy and not args.publish_automatic:parser.error('--deploy에는 --publish-automatic이 필요합니다.')
    # Fail before starting a loop when credentials are absent.
    try:client=DartClient()
    except DartError as exc:
        print(str(exc));raise SystemExit(2) from None
    while True:
        try:
            result=run_once(root,client=client,publish_automatic=args.publish_automatic)
            print('공시 감지 완료:',result,flush=True)
            if args.deploy:
                subprocess.run(['node','scripts/deploy-driver-update.mjs'],cwd=root,check=True)
        except (DartError,ValueError,subprocess.CalledProcessError):
            print('감지 또는 배포 실패: 마지막 공개본 유지. 운영 로그와 연결 상태를 확인하세요.',flush=True)
            if not args.watch:raise SystemExit(1)
        if not args.watch:break
        time.sleep(300)


if __name__=='__main__':main()
