import copy
from pathlib import Path
import unittest
from pipeline.core import load,digest
from pipeline.table_overlays import normalized_rect,validate_overlays

ROOT=Path(__file__).resolve().parents[1]

class TableOverlayTests(unittest.TestCase):
    def setUp(self):self.data=load(ROOT/'public/drivers/samsung-2025-drivers-v1.json')
    def test_every_numeric_cell_maps_back_to_calculation(self):
        validate_overlays(self.data)
        self.assertEqual(sum(len(t['highlights']) for t in self.data['tableOverlays']),16)
        for table in self.data['tableOverlays']:
            self.assertEqual(digest((ROOT/'public'/table['asset']).read_bytes()),table['assetSha256'])
    def test_corrupt_numeric_mapping_rejected(self):
        self.data['tableOverlays'][0]['highlights'][0]['rawValue']='1'
        with self.assertRaises(ValueError):validate_overlays(self.data)
    def test_wrong_report_or_missing_cell_rejected(self):
        self.data['tableOverlays'][0]['sourceSha256']='0'*64
        with self.assertRaises(ValueError):validate_overlays(self.data)
    def test_missing_comparative_cell_rejected(self):
        self.data['tableOverlays'][0]['highlights'].pop()
        with self.assertRaises(ValueError):validate_overlays(self.data)
    def test_coordinates_cannot_escape_original_table(self):
        with self.assertRaises(ValueError):normalized_rect((40,60,70,80),(50,50,100,100))
        self.data['tableOverlays'][0]['highlights'][0]['rect']['x']=1
        with self.assertRaises(ValueError):validate_overlays(self.data)

if __name__=='__main__':unittest.main()
