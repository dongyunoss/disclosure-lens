import copy
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from pipeline.core import calculate, parse_amount, digest, load, save, validate_change, validate_public
from pipeline.parse import parse_report
from pipeline.align import candidate_packets
from pipeline.dart import DartClient, DartError, discover
from pipeline.workflow import prepare, assemble, review, publish, public_payload
from pipeline.llm import completion

def source_xml(year, revenue,profit,prior_revenue,prior_profit):
    return f'''<?xml version="1.0" encoding="UTF-8"?><DOCUMENT><BODY><SECTION-1><TITLE>II. 사업의 내용</TITLE><SECTION-2><TITLE>1. 사업의 개요</TITLE><P>당사는 제품을 공급합니다.</P><P>{year} 제품 설명 문장입니다.</P></SECTION-2></SECTION-1><SECTION-1><TITLE>III. 재무에 관한 사항</TITLE><SECTION-2><TITLE>연결손익계산서</TITLE><P>(단위: 원)</P><TABLE><THEAD><TR><TH>과목</TH><TH>{year}</TH><TH>{year-1}</TH></TR></THEAD><TBODY><TR><TD>매출액</TD><TD>{revenue}</TD><TD>{prior_revenue}</TD></TR><TR><TD>영업이익</TD><TD>{profit}</TD><TD>{prior_profit}</TD></TR></TBODY></TABLE></SECTION-2></SECTION-1></BODY></DOCUMENT>'''.encode()

def archive(xml):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('main.xml',xml)
    return buf.getvalue()

def fixture(root):
    entries=[]
    for year,revenue,profit,prior_revenue,prior_profit in [(2024,1000,-100,900,-150),(2025,1500,100,1000,-100)]:
        receipt=f'{year+1}0101000001';folder=root/'private'/'raw'/'samsung'/receipt;snapshot=folder/'snapshots'/'test';folder.mkdir(parents=True)
        raw=archive(source_xml(year,revenue,profit,prior_revenue,prior_profit));(folder/'source.zip').write_bytes(raw)
        report=dict(id=f'samsung-{receipt}',companyId='samsung',year=year,receipt=receipt,filedAt=f'{year+1}-01-01',corrected=False,checkedAt='2026-09-12T00:00:00+00:00',sha256=digest(raw),dartUrl=f'https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt}')
        accounts=[dict(rcept_no=receipt,fs_div='CFS',reprt_code='11011',bsns_year=str(year),account_nm=label,thstrm_amount=str(amount),currency='KRW') for label,amount in [('매출액',revenue),('영업이익',profit)]]
        save(snapshot/'report.json',report);save(snapshot/'accounts.json',accounts)
        entries.append(dict(companyId='samsung',year=year,receipt=receipt,path=str(folder.relative_to(root)),snapshot=str(snapshot.relative_to(root))))
    save(root/'private'/'collection.json',entries)
    save(root/'public'/'data'/'catalog.json',dict(schemaVersion=1,companies=[dict(id='samsung',name='삼성전자',stockCode='005930',comparisons=[])]))
    folder=prepare(root,'samsung');data=load(folder/'draft.json');bindings=load(folder/'bindings.template.json')
    for key,row in [('revenue',0),('operating_income',1)]:
        for side,i in [('before',0),('after',1)]:
            b=next(b for b in data['evidence'] if b['reportId']==data['reports'][i]['id'] and b['kind']=='table')
            bindings[key][side].update(blockId=b['id'],row=row)
    save(folder/'bindings.json',bindings);assemble(root,'samsung')
    return folder

class FinancialTests(unittest.TestCase):
    def test_large_integer_precision(self):
        r=calculate('900719925474099300000','900719925474099300001');self.assertEqual(r['delta'],'1')
    def test_growth(self):self.assertEqual(calculate('100','118')['percent'],'18.00')
    def test_zero(self):self.assertIsNone(calculate('0','10')['percent'])
    def test_profit_transition(self):self.assertEqual(calculate('-100','10')['status'],'흑자 전환')
    def test_loss_transition(self):self.assertEqual(calculate('100','-10')['status'],'적자 전환')
    def test_loss_widening(self):self.assertEqual(calculate('-100','-150')['status'],'적자 확대')
    def test_loss_narrowing(self):self.assertEqual(calculate('-100','-50')['status'],'적자 축소')
    def test_restatement(self):self.assertIsNone(calculate('100','150',prior_comparative='110')['percent'])
    def test_basis_mismatch(self):self.assertIsNone(calculate('100','150',compatible=False)['percent'])
    def test_unit_conversion(self):self.assertEqual(parse_amount('(1,234)',1000000),'-1234000000')
    def test_missing_not_zero(self):
        for value in ['-','','N/A','NaN','Infinity']:
            with self.assertRaises(ValueError):parse_amount(value)

class SourceTests(unittest.TestCase):
    def setUp(self):self.report=dict(id='samsung-test',year=2024)
    def test_table_and_context_and_stable_ids(self):
        raw=archive(source_xml(2024,100,-10,90,-20));blocks=parse_report(raw,self.report)
        self.assertEqual(blocks,parse_report(raw,self.report));table=next(b for b in blocks if b['kind']=='table')
        self.assertEqual(table['rows'][0],['매출액','100','90']);self.assertIn('원',table['contextBefore']);self.assertIn('연결',table['section'])
    def test_xml_entities_rejected(self):
        with self.assertRaises(Exception):parse_report(archive(b'<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>'),self.report)
    def test_ambiguous_document_rejected(self):
        with self.assertRaises(ValueError):parse_report(archive(b'<ROOT><P>not a report</P></ROOT>'),self.report)
    def test_split_merge_candidates(self):
        b=lambda i,t,o:dict(id=i,reportId=i[0],kind='paragraph',section='사업의 개요',text=t,normalized=t,order=o,contextBefore='',contextAfter='')
        packets=candidate_packets([b('a1','제품을 제공합니다.',1),b('a2','서비스도 제공합니다.',2)],[b('b1','제품과 서비스를 제공합니다.',1)])
        self.assertEqual(len(packets[0]['before']),2);self.assertEqual(len(packets[0]['after']),1)
    def test_identical_moved_ignored(self):
        b=dict(id='a',reportId='a',kind='paragraph',section='사업의 개요',text='같은 문장',normalized='같은 문장',order=1,contextBefore='',contextAfter='')
        self.assertEqual(candidate_packets([b],[dict(b,id='b',reportId='b',order=5)]),[])
    def test_fabricated_quote_rejected(self):
        blocks={'a':dict(id='a',reportId='old',kind='paragraph',section='사업의 개요',text='실제 문장')}
        c=dict(kind='removed',title='삭제',explanation='설명',before=[dict(blockId='a',quote='가짜 문장')],after=[])
        with self.assertRaises(ValueError):validate_change(c,blocks,'old','new')
    def test_moved_not_removed(self):
        a=dict(id='a',reportId='old',kind='paragraph',section='사업의 개요',text='실제 문장');b=dict(a,id='b',reportId='new')
        c=dict(kind='removed',title='삭제',explanation='설명',before=[dict(blockId='a',quote='실제 문장')],after=[])
        with self.assertRaises(ValueError):validate_change(c,{'a':a,'b':b},'old','new')

class PublicationTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.folder=fixture(self.root)
    def tearDown(self):self.temp.cleanup()
    def test_unreviewed_draft_blocked(self):
        with self.assertRaises(FileNotFoundError):publish(self.root,'samsung')
    def test_review_ack_required(self):
        with self.assertRaises(ValueError):review(self.root,'samsung','Tester',False)
    @patch('pipeline.release.release_gate', return_value={'passed':True})
    def test_publish_and_idempotency(self, release_gate):
        review(self.root,'samsung','Test-only reviewer',True);path=publish(self.root,'samsung')
        out=load(self.root/'public'/path);self.assertEqual(out['mode'],'reviewed');self.assertNotIn('reviewer',json.dumps(out))
        self.assertEqual(publish(self.root,'samsung'),path)
    def test_missing_real_release_checks_blocks_publication(self):
        review(self.root,'samsung','Test-only reviewer',True)
        with self.assertRaises(FileNotFoundError):publish(self.root,'samsung')
    def test_modified_after_review_rejected(self):
        review(self.root,'samsung','Test-only reviewer',True);data=load(self.folder/'draft.json');data['financials'][0]['after']='999';save(self.folder/'draft.json',data)
        with self.assertRaises(ValueError):publish(self.root,'samsung')
    def test_modified_evidence_rejected(self):
        data=load(self.folder/'draft.json');data['evidence'][0]['text']='변조';save(self.folder/'draft.json',data)
        with self.assertRaises(ValueError):review(self.root,'samsung','Tester',True)
    def test_unit_mismatch_rejected(self):
        binding=load(self.folder/'bindings.json');binding['revenue']['before']['multiplier']=1000000;save(self.folder/'bindings.json',binding)
        with self.assertRaises(ValueError):assemble(self.root,'samsung')
    def test_wrong_receipt_requires_manual_review(self):
        accounts=load(self.folder/'accounts.json')
        for rows in accounts.values():
            for row in rows:row['rcept_no']='WRONG'
        save(self.folder/'accounts.json',accounts)
        with self.assertRaises(ValueError):assemble(self.root,'samsung')
    def test_internal_fields_excluded(self):
        data=load(self.folder/'draft.json');data['secret']='hidden';data['reports'][0]['internalNote']='hidden';data['evidence'][0]['internalNote']='hidden'
        self.assertNotIn('hidden',json.dumps(public_payload(data,'test')))
    def test_demo_rejected(self):
        with self.assertRaises(ValueError):validate_public(dict(schemaVersion=1,mode='demo'))

class NetworkTests(unittest.TestCase):
    def test_missing_key(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(DartError):DartClient()
    def test_quota_does_not_retry(self):
        class Resp:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return b'{"status":"020"}'
        with patch('urllib.request.urlopen',return_value=Resp()) as request:
            with self.assertRaises(DartError):DartClient('not-a-real-key').request('list.json')
            self.assertEqual(request.call_count,1)
    def test_latest_corrected_report(self):
        class Client:
            def request(self,*a,**k):return dict(total_page=1,list=[dict(report_nm='사업보고서 (2024.12)',rcept_no='20250301000001'),dict(report_nm='[기재정정]사업보고서 (2024.12)',rcept_no='20250601000001'),dict(report_nm='사업보고서 (2025.12)',rcept_no='20260301000001')])
        self.assertEqual(discover(Client(),'test')[2024]['rcept_no'],'20250601000001')
    def test_budget_prevents_network(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,dict(LLM_API_KEY='test',LLM_MODEL='test',LLM_BASE_URL='https://example.com/v1',LLM_INPUT_KRW_PER_MILLION='10000',LLM_OUTPUT_KRW_PER_MILLION='10000',LLM_MONTHLY_BUDGET_KRW='0.001')),patch('urllib.request.urlopen') as request:
            with self.assertRaises(ValueError):completion(Path(tmp),dict(before=[],after=[]))
            request.assert_not_called()

if __name__=='__main__':unittest.main()
