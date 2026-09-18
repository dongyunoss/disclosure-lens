import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pipeline.core import load, save
from pipeline.drivers import fcf_bridge, revenue_bridge, validate_analysis
from pipeline.live_analysis import account_pair
from pipeline.monitor import classify, run_once
from pipeline.dart import DartError

ROOT=Path(__file__).resolve().parents[1]

class DriverTests(unittest.TestCase):
    def test_capex_decline_exact(self):
        x=fcf_bridge(dict(cfo='100',ppe='20',intangibles='5'),dict(cfo='110',ppe='60',intangibles='10'))
        self.assertEqual((x['before'],x['after'],x['delta']),('75','40','-35'))
        self.assertEqual([p['impact'] for p in x['components']],['10','-40','-5'])
    def test_missing_not_zero(self):
        with self.assertRaises(ValueError):fcf_bridge(dict(cfo='100',ppe='20'),dict(cfo='100',ppe='20',intangibles='0'))
    def test_negative_cash_flow_and_precision(self):
        x=fcf_bridge(dict(cfo='9007199254740993',ppe='0',intangibles='0'),dict(cfo='-10',ppe='10',intangibles='0'))
        self.assertEqual(x['delta'],'-9007199254741013')
    def test_negative_outflow_rejected(self):
        with self.assertRaises(ValueError):fcf_bridge(dict(cfo='1',ppe='-1',intangibles='0'),dict(cfo='1',ppe='1',intangibles='0'))
    def test_regional_residual_not_hidden(self):
        x=revenue_bridge('100','140',[dict(label='유럽',before='30',after='50')])
        self.assertEqual(x['residual'],'20');self.assertEqual(x['components'][-1]['impact'],'20')
    def test_zero_denominator_no_share(self):
        x=revenue_bridge('100','100',[dict(label='유럽',before='20',after='30')])
        self.assertTrue(all(p['share'] is None for p in x['components']))
    def test_reclassification_rejected(self):
        with self.assertRaises(ValueError):revenue_bridge('10','20',[],comparable=False)
    def test_actual_data_and_tampering(self):
        x=load(ROOT/'public/drivers/samsung-2025-drivers-v1.json');validate_analysis(x)
        self.assertEqual(x['metrics'][0]['delta'],'13921017000000')
        x['metrics'][0]['components'][0]['after']='1'
        with self.assertRaises(ValueError):validate_analysis(x)

class LiveAccountTests(unittest.TestCase):
    def setUp(self):
        self.f=dict(receipt='20260918000001',year=2026,reportCode='11012',url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260918000001')
        self.row=dict(rcept_no=self.f['receipt'],bsns_year='2026',reprt_code='11012',currency='KRW',sj_div='IS',account_id='ifrs-full_Revenue',account_nm='매출액',thstrm_amount='50',frmtrm_q_amount='40',thstrm_add_amount='90',frmtrm_add_amount='70')
    def test_ytd_not_quarter(self):
        a,b,_=account_pair([self.row],'revenue',self.f);self.assertEqual((a,b),('70','90'))
    def test_missing_ytd_never_falls_back_to_quarter(self):
        del self.row['thstrm_add_amount']
        with self.assertRaises(ValueError):account_pair([self.row],'revenue',self.f)
    def test_receipt_currency_and_separate_rejected(self):
        for key,value in [('rcept_no','20260917000001'),('currency','USD'),('fs_div','OFS')]:
            row={**self.row,key:value}
            with self.assertRaises(ValueError):account_pair([row],'revenue',self.f)
    def test_duplicate_ambiguous_account(self):
        with self.assertRaises(ValueError):account_pair([self.row,self.row],'revenue',self.f)
    def test_outflow_semantics(self):
        row={**self.row,'sj_div':'CF','account_id':'ifrs-full_PurchaseOfPropertyPlantAndEquipment','account_nm':'유형자산의 취득','thstrm_amount':'(12)','frmtrm_q_amount':'(10)'}
        a,b,_=account_pair([row],'ppe',self.f);self.assertEqual((a,b),('10','12'))

class FakeClient:
    def __init__(self, rows):self.rows=rows;self.fail=False
    def request(self, endpoint, **params):
        if self.fail:raise DartError('OpenDART 연결 실패')
        return dict(list=self.rows,total_page=1)

class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.row=dict(report_nm='반기보고서 (2026.06)',rcept_no='20260918000001',rcept_dt='20260918',rm='')
        self.client=FakeClient([self.row]);self.clock=datetime(2026,9,18,tzinfo=timezone.utc);self.calls=0
        save(self.root/'private/monitor/state.json',dict(schemaVersion=1,codes={'samsung':'00126380'},companies={},jobs={}))
    def tearDown(self):self.temp.cleanup()
    def analyze(self,root,client,filing):
        self.calls+=1
        x=load(ROOT/'public/drivers/samsung-2025-drivers-v1.json');x['id']='samsung-'+filing['receipt'];return x
    def run_worker(self,**kwargs):return run_once(self.root,client=self.client,clock=self.clock,analyzer=self.analyze,**kwargs)
    def test_dedup_and_new_correction(self):
        self.run_worker();self.run_worker();self.assertEqual(self.calls,1)
        self.client.rows=[{**self.row,'report_nm':'[기재정정]반기보고서 (2026.06)','rcept_no':'20260918000002'}]
        self.run_worker();self.assertEqual(self.calls,2)
    def test_draft_default_and_explicit_publish(self):
        self.run_worker();self.assertFalse((self.root/'public/drivers/catalog.json').exists())
    def test_automatic_publish_validated(self):
        self.run_worker(publish_automatic=True)
        c=load(self.root/'public/drivers/catalog.json');self.assertEqual(c['items'][0]['status'],'automatic')
    def test_retry_backoff(self):
        def fail(*args):raise ValueError('API 데이터 갱신 전')
        run_once(self.root,client=self.client,clock=self.clock,analyzer=fail)
        self.run_worker();self.assertEqual(self.calls,0)
        self.clock+=timedelta(minutes=6);self.run_worker();self.assertEqual(self.calls,1)
    def test_query_failure_keeps_cursor_and_previous_results(self):
        self.run_worker(publish_automatic=True);old=load(self.root/'private/monitor/state.json')['companies'];self.client.fail=True
        self.clock+=timedelta(days=1);self.run_worker()
        self.assertEqual(load(self.root/'private/monitor/state.json')['companies'],old)
        self.assertTrue(load(self.root/'public/drivers/catalog.json')['items'])
        self.assertEqual(load(self.root/'public/drivers/monitor.json')['state'],'degraded')
    def test_provisional_cannot_invent_cashflow(self):
        self.client.rows=[{**self.row,'report_nm':'연결재무제표기준영업(잠정)실적(공정공시)'}]
        self.run_worker();self.assertEqual(self.calls,0)
        self.assertEqual(load(self.root/'public/drivers/monitor.json')['filings'][0]['status'],'source_pending')
    def test_no_separate_year_and_half_year_mix(self):
        self.assertEqual(classify(self.row,'samsung','00126380')['reportCode'],'11012')
        self.assertIsNone(classify({**self.row,'rm':'철'},'samsung','00126380'))

if __name__=='__main__':unittest.main()
