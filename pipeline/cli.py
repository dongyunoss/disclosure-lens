import argparse
import os
import sys
from pathlib import Path
from .core import COMPANIES, load, save, validate_public

ROOT=Path(__file__).resolve().parents[1]

def env_file(root):
    path=root/'.env'
    if not path.exists():return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            key,value=line.split('=',1);key=key.strip()
            if key in {'DART_API_KEY','LLM_API_KEY','LLM_BASE_URL','LLM_MODEL','LLM_INPUT_KRW_PER_MILLION','LLM_OUTPUT_KRW_PER_MILLION','LLM_MONTHLY_BUDGET_KRW'}:os.environ.setdefault(key,value.strip().strip('"').strip("'"))

def main():
    parser=argparse.ArgumentParser(description='공시렌즈 · 수집 → 추출 → 분석 → 검수 → 공개')
    parser.add_argument('command',choices=['collect','check-updates','prepare','analyze','assemble','review','publish','validate-public','demo','evaluate'])
    parser.add_argument('--company',choices=list(COMPANIES));parser.add_argument('--reviewer',default='');parser.add_argument('--acknowledge',action='store_true');parser.add_argument('--truth');parser.add_argument('--predictions')
    args=parser.parse_args();env_file(ROOT)
    try:
        if args.command=='demo':
            from .demo import generate
            generate(ROOT);print('별도 가상 예시 생성 완료');return
        if args.command=='validate-public':
            catalog=load(ROOT/'public'/'data'/'catalog.json')
            for company in catalog['companies']:
                for pair in company['comparisons']:
                    relative=Path(pair['path']);dest=(ROOT/'public'/relative).resolve()
                    if not dest.is_relative_to((ROOT/'public'/'data').resolve()):raise ValueError('잘못된 공개 데이터 경로')
                    data=load(dest);validate_public(data)
                    if data['companyId']!=company['id'] or data['id']!=pair['id'] or pair['mode']!='reviewed':raise ValueError('목록과 결과 정보가 다릅니다.')
            print('공개 데이터 검증 완료 (수집 전 목록은 빈 상태 유지)');return
        if args.command=='collect':
            from .dart import collect
            result=collect(ROOT,[args.company] if args.company else None);print(f'{len(result)}개 보고서 수집 완료');return
        if args.command=='check-updates':
            from .dart import DartClient, corporation_codes, discover
            client=DartClient();codes=corporation_codes(client);old=load(ROOT/'private'/'collection.json') if (ROOT/'private'/'collection.json').exists() else []
            changes=[]
            for cid in ([args.company] if args.company else COMPANIES):
                for year,item in discover(client,codes[cid]).items():
                    previous=next((x for x in old if x['companyId']==cid and x['year']==year),None)
                    if not previous or previous['receipt']!=item['rcept_no']:changes.append(dict(companyId=cid,year=year,receipt=item['rcept_no']))
            save(ROOT/'private'/'updates.json',changes);print(f'신규·정정 보고서 {len(changes)}개. 공개본은 변경하지 않았습니다.');return
        if args.command=='evaluate':
            from .evaluate import evaluate
            if not args.truth or not args.predictions:raise ValueError('--truth와 --predictions를 지정하세요.')
            result=evaluate(args.truth,args.predictions);print(result)
            if not result['passed']:sys.exit(1)
            return
        if not args.company:raise ValueError('--company를 지정하세요.')
        from . import workflow
        if args.command=='review':workflow.review(ROOT,args.company,args.reviewer,args.acknowledge);print('검수 확인 기록 완료')
        else:print(getattr(workflow,args.command)(ROOT,args.company))
    except (ValueError,RuntimeError,KeyError,FileNotFoundError,IndexError) as exc:
        print(f'작업 중단: {exc}',file=sys.stderr);sys.exit(1)

if __name__=='__main__':main()
