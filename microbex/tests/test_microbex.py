
# ### test input/ output for user testing
# import pandas as pd
# import os
# import numpy as np

# import pathlib
# import re
# import sys, warnings
# # from datetime import date

# import time
# # from .parameters import *

# ##changed src->microbex
# import MicrobEx.microbex.microbex as me

# from .utils.ohdsi_mapping import OHDSI_NAME, OHDSI_ID
# from .utils.regex_blocks import value_map_dict, value_map_dict2, quant_regex_list, specimen_regex_list, negative_regex_list
# from .utils.regex_blocks import virus_regex_list, yeast_regex_list, staph_regex_dic, staph_classification_dic, staph_name_dic
# from microbex.utils.regex_blocks import pos_quant_list, pos_qual_list, species_regex_list, unclear_regex_list, likely_negative_regex_list

# ##importing data
# from microbex.sample_data.sample_data import sample_df, sample_annotation

# #import MicrobEx


# def test_script1(annotated_MicrobEx):
#     ###ensuring the MicrobEx object argument provided has a annotated_data, if not, run annotation
#     if hasattr(annotated_MicrobEx, 'annotated_data') ==False:
#         annotated_MicrobEx.annotate(staph_neg_correction=True,
#               specimen_col=None,
#               review_suggestions=False,
#               likelyneg_block_skip=False)
    
#     try:
#         compare_df_bool=annotated_MicrobEx.annotated_data==sample_annotation
#     except BaseException:
# #         print(f"Unexpected {err=}, {type(err)=}")
#         raise RuntimeError('Error occured when comparing previously run sample_annotation w/ freshly run test_data.annotate()') 
        
#     if compare_df_bool==False:
#         for element in list(sample_annotation):
#             if sample_annotation.loc[:,element]!=annotated_MicrobEx.annotated_data.loc[:,element]:
#                 print('{} column does not match the expected annotation col'.format(element))
                
        
# def test_script2(annotated_MicrobEx):
#     ##check params:
#     if (obj1.run_params!=annotated_params):
#         raise RuntimeError('MicrobEx.annotate() saved parameters (default) do not match run parameters') 
    



# def main():
#     ###previously annotated and run data:
#     annotated_params={'staph_neg_correction': False,
#                      'specimen_col': None,
#                      'review_suggestions': False,
#                      'likelyneg_block_skip': False}
# #     sample_annotation=pd.read_csv('sample_data/sample_annotation.csv')

#     ###raw data used in above annotation:
# #     sample_df=pd.read_csv('sample_data/sample_data.csv')


#     ###running MicrobEx on raw sampele data

#     # instantiating
#     obj1= me.Microbex(sample_df,
#                   text_col='parsed_note',
#                   culture_id_col='culture_id',
#                   visit_id_col='visit_id')

#     obj1.annotate(staph_neg_correction=True,
#                   specimen_col=None,
#                   review_suggestions=False,
#                   likelyneg_block_skip=False
#                  )
    
    
#     test_script1(obj1)
#     test_script2(obj1)
    
    
# if __name__ == "__main__":
#     main()
    
    
    
    
    
    
# ####pseduo 

# self.assertTrue(sample_annotation==annotated, ) 
# ## JUST DO COL COMPARISON

## 
import pytest
import unittest
import microbex.microbex as me
import pandas as pd


class TestMicrobex(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.sample_df = pd.read_csv('microbex/sample_data/sample_data.csv')#.sort_values(['culture_id','visit_id','parsed_note'])
#         cls.sample_annotation = pd.read_csv('microbex/sample_data/sample_annotation.csv')#.sort_values(['culture_id','visit_id','parsed_note'])
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


# print(obj1.annotated_data.head())