
### unit test to ensure a freshly annotated reference dataset = a saved annotated version of the same dataset.

import pytest
import unittest
import microbex.microbex as me
import pandas as pd


class TestMicrobex(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.sample_df = pd.read_csv('microbex/sample_data/sample_data.csv')#.sort_values(['culture_id','visit_id','parsed_note'])
        cls.sample_annotation = pd.read_pickle('microbex/sample_data/sample_annotation.pkl') # pkl saves columns of lists better than csv. 
    
    def test_compare(self):
    
        obj1= me.Microbex(
            self.sample_df,
            text_col='parsed_note',
            culture_id_col='culture_id',
            visit_id_col='visit_id'
        )
        obj1.annotate(
            staph_neg_correction=False, 
            specimen_col=None,
            review_suggestions=False,
            likelyneg_block_skip=False
        )

        ##comparing each colvector.
        for element in list(self.sample_annotation):
            print('###################{}##################'.format(element))
            self.assertTrue(min(self.sample_annotation[element]==obj1.annotated_data[element]), f"{element}") #assertion: if this thing fails, raise an error. 


