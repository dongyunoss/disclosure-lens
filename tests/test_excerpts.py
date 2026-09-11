import copy
import unittest
from pathlib import Path
from pipeline.core import load
from pipeline.excerpts import extract_passage,extract_row,validate_library
ROOT=Path(__file__).resolve().parents[1]
class ExcerptTests(unittest.TestCase):
    def test_exact_passage_preserves_line_breaks(self):
        self.assertEqual(extract_passage('앞 SDC 및 회사\n사업입니다. 뒤','SDC','사업입니다.'),'SDC 및 회사\n사업입니다.')
    def test_missing_selector_fails(self):
        with self.assertRaises(ValueError):extract_passage('원문','없음','문장')
    def test_row_keeps_footnote_and_order(self):
        quote,values=extract_row('매출액 (주30) 333,605,938 300,870,903 258,935,494','매출액')
        self.assertIn('(주30)',quote);self.assertEqual(values,['333,605,938','300,870,903','258,935,494'])
    def test_ambiguous_row_fails(self):
        with self.assertRaises(ValueError):extract_row('매출액 1,000 2,000 3,000\n매출액 4,000 5,000 6,000','매출액')
    def test_actual_library_validates(self):
        validate_library(load(ROOT/'public'/'excerpts'/'library.json'))
    def test_missing_provenance_fails(self):
        data=load(ROOT/'public'/'excerpts'/'library.json');data['sources'][0]['sha256']=''
        with self.assertRaises(ValueError):validate_library(data)
    def test_false_latest_correction_claim_fails(self):
        data=load(ROOT/'public'/'excerpts'/'library.json');data['sources'][0]['latestCorrectionVerified']=True
        with self.assertRaises(ValueError):validate_library(data)
    def test_public_quote_length_limit(self):
        data=load(ROOT/'public'/'excerpts'/'library.json');data['sources'][0]['excerpts'][0]['quote']='word '*26
        with self.assertRaises(ValueError):validate_library(data)
