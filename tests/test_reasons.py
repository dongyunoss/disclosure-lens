import unittest
from pipeline.reasons import validate_claims
from pipeline.regions import extract_regions

class ReasonTests(unittest.TestCase):
    def setUp(self):
        self.blocks=[dict(id='b1',text='유럽 지역 매출은 판매 물량 증가로 늘었습니다.')]
        self.claim=dict(metric='revenue',blockId='b1',quote=self.blocks[0]['text'],explanation='회사는 물량 증가를 설명합니다.',evidenceLevel='company_statement',missingEvidence='')
    def test_claims_always_need_review(self):
        self.assertEqual(validate_claims(dict(claims=[self.claim]),self.blocks)['claims'][0]['reviewStatus'],'needs_review')
    def test_fabricated_quote_rejected(self):
        self.claim['quote']='유럽 수출이 늘었다'
        with self.assertRaises(ValueError):validate_claims(dict(claims=[self.claim]),self.blocks)
    def test_hypothesis_requires_missing_evidence(self):
        self.claim['evidenceLevel']='hypothesis'
        with self.assertRaises(ValueError):validate_claims(dict(claims=[self.claim]),self.blocks)
    def test_unrelated_source_rejected(self):
        self.claim['blockId']='unrelated'
        with self.assertRaises(ValueError):validate_claims(dict(claims=[self.claim]),self.blocks)

class RegionTests(unittest.TestCase):
    def setUp(self):
        self.f=dict(reportCode='11011',year=2025,url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260310000001')
        self.block=dict(id='table',kind='table',section='연결 주석 > 지역별 매출',unit='단위: 원',headers=['지역','2025','2024'],rows=[['유럽','50','30'],['미주','90','70'],['합계','140','100']],text='원문 표')
    def test_verified_period_and_total(self):
        metric,ref=extract_regions([self.block],self.f,'100','140')
        self.assertEqual(metric['components'][0]['impact'],'20');self.assertEqual(ref['id'],'table')
    def test_scope_mismatch_or_partial_is_not_a_cause(self):
        self.assertIsNone(extract_regions([self.block],self.f,'100','200'))
        self.block['section']='별도 지역별 매출'
        self.assertIsNone(extract_regions([self.block],self.f,'100','140'))
    def test_quarter_period_not_assumed(self):
        self.f['reportCode']='11012';self.assertIsNone(extract_regions([self.block],self.f,'100','140'))
    def test_duplicate_tables_require_review(self):
        self.assertIsNone(extract_regions([self.block,self.block],self.f,'100','140'))
