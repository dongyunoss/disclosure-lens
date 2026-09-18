import copy
import unittest
from pathlib import Path
from pipeline.core import load
from pipeline.investment_review import screen, validate_review

ROOT=Path(__file__).resolve().parents[1]


class InvestmentReviewTests(unittest.TestCase):
    def setUp(self):
        self.data=load(ROOT/'public/review/samsung-2025-review-v1.json')
        self.facts=copy.deepcopy(self.data['facts'])

    def finding(self, key): return next(f for f in screen(self.facts) if f['id']==key)
    def set_value(self,key,side,value): next(f for f in self.facts if f['id']==key)[side]=value

    def test_actual_values_cells_and_calculations(self):
        validate_review(self.data,ROOT)
        self.assertEqual(len(self.facts),20)
        self.assertEqual(self.finding('receivables')['status'],'attention')
        self.assertEqual(self.finding('margin')['status'],'movement')
        self.assertEqual(self.finding('inventory')['status'],'not_triggered')
        self.assertEqual(self.finding('working-capital')['status'],'attention')
        self.assertEqual(self.finding('short-debt')['status'],'attention')
        self.assertEqual(self.finding('cash-quality')['status'],'not_triggered')
        self.assertEqual(self.finding('investment')['stats'][1]['value'],'331619.99')

    def test_missing_data_is_not_a_clear_result(self):
        self.facts=[f for f in self.facts if f['id']!='receivables']
        self.assertEqual(self.finding('receivables')['status'],'unavailable')

    def test_nonpositive_denominators_withhold_judgment(self):
        for value in ['0','-100']:
            self.set_value('net_income','after',value)
            self.assertEqual(self.finding('cash-quality')['status'],'unavailable')
        self.set_value('revenue','before','0')
        self.assertEqual(self.finding('receivables')['status'],'unavailable')

    def test_boundary_is_exact(self):
        for side in ['before','after']: self.set_value('revenue',side,'100000000000000000000')
        self.set_value('receivables','before','100000000000000000000')
        self.set_value('receivables','after','104999999999999999999')
        self.assertEqual(self.finding('receivables')['status'],'not_triggered')
        self.set_value('receivables','after','105000000000000000000')
        self.assertEqual(self.finding('receivables')['status'],'attention')

    def test_negative_fcf_and_positive_payout_flags(self):
        self.set_value('cfo','after','1')
        self.assertEqual(self.finding('payout')['status'],'attention')

    def test_negative_operating_profit_is_attention(self):
        self.set_value('operating','after','-100')
        self.assertEqual(self.finding('margin')['status'],'attention')

    def test_improving_loss_still_requires_attention(self):
        self.set_value('operating','before','-200000000000000')
        self.set_value('operating','after','-100000000000000')
        self.assertEqual(self.finding('margin')['status'],'attention')

    def test_negative_cash_requires_attention_even_when_ratio_undefined(self):
        self.set_value('net_income','after','-100')
        self.set_value('cfo','after','-200')
        self.assertEqual(self.finding('cash-quality')['status'],'attention')

    def test_outflow_sign_rejected(self):
        self.set_value('ppe','after','-100')
        with self.assertRaises(ValueError):screen(self.facts)

    def test_tampered_results_and_values_rejected(self):
        d=copy.deepcopy(self.data);d['findings'][0]['status']='attention'
        with self.assertRaises(ValueError):validate_review(d)
        d=copy.deepcopy(self.data);d['facts'][0]['after']='9999999'
        d['findings']=screen(d['facts'])
        with self.assertRaises(ValueError):validate_review(d)

    def test_duplicate_fact_rejected(self):
        with self.assertRaises(ValueError):screen(self.facts+[self.facts[0]])

    def test_nonannual_or_separate_basis_rejected(self):
        for k,v in [('periodType','quarterly'),('basis','별도'),('currency','USD')]:
            d=copy.deepcopy(self.data);d[k]=v
            with self.assertRaises(ValueError):validate_review(d)


if __name__=='__main__':unittest.main()
