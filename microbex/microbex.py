
### <insert> import preamble 

import pandas as pd
import os
import numpy as np

import pathlib
import re
import sys, warnings

import time
from microbex.utils.ohdsi_mapping import OHDSI_NAME, OHDSI_ID
from microbex.utils.regex_blocks import value_map_dict, value_map_dict2, quant_regex_list, specimen_regex_list, negative_regex_list
from microbex.utils.regex_blocks import virus_regex_list, yeast_regex_list, staph_regex_dic, staph_classification_dic, staph_name_dic
from microbex.utils.regex_blocks import pos_quant_list, pos_qual_list, species_regex_list, unclear_regex_list, likely_negative_regex_list


class Microbex:

    
    def __init__(self, 
                 data,#: pd.core.frame.DataFrame, ###check if this requirement works. can work on this late.
                 text_col,#: str, #previously text_col_main
                 culture_id_col,#: str, #previously culture_id_main
                 visit_id_col,#: str, #previously visit_id_main
                ):
              
        if type(data)!=pd.core.frame.DataFrame:
            raise TypeError("data argument has unsupported dtype:", type(data))
            
        if type(text_col)!=str:
            raise TypeError("text_col argument has unsupported dtype:", type(text_col))
        
        if type(culture_id_col)!=str:
            raise TypeError("culture_id_col argument has unsupported dtype:", type(culture_id_col))
        
        if type(visit_id_col)!=str:
            raise TypeError("visit_id_col argument has unsupported dtype:", type(visit_id_col))
            
        ##arg attributes
        self.raw_data= data.copy()
        self.text_col= text_col
        self.visit_id_col = visit_id_col ## 
        self.culture_id_col = culture_id_col ## 

        ##instantiated regex lists
        self.value_map_dict= value_map_dict
        self.value_map_dict2=value_map_dict2
        self.quant_regex_list= quant_regex_list
        self.specimen_regex_list= specimen_regex_list
        self.negative_regex_list = negative_regex_list
        self.virus_regex_list= virus_regex_list
        self.yeast_regex_list= yeast_regex_list
        self.staph_regex_dic= staph_regex_dic
        self.staph_classification_dic= staph_classification_dic
        self.staph_name_dic= staph_name_dic
        self.pos_quant_list= pos_quant_list
        self.pos_qual_list= pos_qual_list
        self.species_regex_list= species_regex_list
        self.unclear_regex_list= unclear_regex_list
        self.likely_negative_regex_list= likely_negative_regex_list
        self.OHDSI_ID_DIC = OHDSI_ID
        self.OHDSI_NAME_DIC = OHDSI_NAME
        
#         ###typecheck error loop instead of instant. needs to be implemented
#         loop_list=[self.likelyneg_capt, self.likelyneg_regex, ...]
#         for element in loop_list:
#             if type(element != pd.core.series.Series):
#                 raise TypeError("attribute {} is not in a pandas series datatype format".format(element))
        

    
    def annotate(self, 
                 specimen_col=None,#: str=None,
                 staph_neg_correction=False,#: bool=False,
                 review_suggestions=False,#: bool=False,
                 likelyneg_block_skip=False,#: bool=False,
                verbose=True,#: bool=True
                ):
        
        """       
            function: method to perform all steps of microbiology note annotation. key annotations include total_species_capture (all bacteria+virus+fungi species mentioned), and
            binary bacteria positive culture status (1=positive, 0=negative). annotation() creates an class_attribute: obj.annotated_data with all associated annotations 
            following a roughly 7 step process:
            
            0: simple cleaning of parsed_note + annotation of descriptive info for specimen and quantitative information 
            1: parses blatent negative results and non-bacterial species.
            2: sequestering the rows with a negative capture from rows without any capture before downstream positive annotations.
            3: annotates unspecific positive rows. greedy but will be overwritten by more specific parsings later when possible
            4: annotates species specific positives.
            5: annotates staph positives with (optional setting) handling for coagulase negative staph
            6: annotates any previously positive row with unclear language. eg "unable to determine presence or absence of staph...". 
            7: final datastructure management, mapping species captures to OHDSI ontology, and finalizing positive culture status annotation. 
            staph_neg_correction: default True. True means the staph_neg correction runs, aka requires multiple instances of coag_neg to = outcome positive. False: all staph = Positive regardless of type or # of occurances.

                    kwargs:
                            specimen_col (str): default None;
                            staph_neg_correction (bool):default False;
                            review_suggestions (bool): default False;
                            likelyneg_block_skip (bool): default False; likelyneg captures impact classification -> negative. if True, likelyneg regex_block captures don't influence classification.
                            verbose (bool): default True; changes the amount of text offered during annotate() runs.
                    Returns:
                            microbex class object will have 2 additional attributes: annotated_data (final annotated version of raw_data) and annotate_params (record of kwargs used in annotate())
        """

        def df_split_regex(df, result_binary_regex_split=None):
            """
            function to segregate a dataframe into two dataframes based a boolean list obtained from applying a regex_match to a col of results. intended to be used to sequester a dataframe of classified rows into positives and negatives
            """
            if result_binary_regex_split is not None:
                bool_list=df['pos_culture_audit1'].apply(lambda x: re.search(result_binary_regex_split,str(x).lower()) is not None)
                df_unclass=df.loc[bool_list,:].copy()
                df=df.drop(df.loc[bool_list,:].index)
            else:
                df_unclass= df.loc[df['pos_culture_audit1']=='not_captured',:].copy()
                df=df.drop(df.loc[df['pos_culture_audit1']=='not_captured',:].index)

            return(df, df_unclass)

        def selective_append(x, element):
            """
            simple append function with some if/then logic, slightly larger than ideal in a lamba fxn. 
            """
            if type(x)== list:
                 x.append(staph_name_dic[element])
                    
                    
        def final_multiorg_adjustment(df):
            """
            adjusting final classification, and species_capt for those with the generalized multiple species present and no other info present. 
            ### taking the rows wwith a non-specific multipositive, and possibly some unclea rlanguage, and no species in species_capt. adding unspecified organisms to species list in this case. 

            """
            ### adding multiple_organisms present
            t1= df[['pos_qual_capt']].explode('pos_qual_capt')#[UC_culture_cat['pos_qual_capt'].explode()=='multiple organisms present']
            t1_index=t1[t1['pos_qual_capt']=='multiple organisms present'].index

            df.loc[t1_index,'pos_culture_status']=1 #adjusting the resultnum to be positive if multiorg is present. 
            df.loc[t1_index,'pos_culture_audit1']='multiorg_pos1'

            ### taking the rows wwith a non-specific multipositive, and possibly some unclea rlanguage, and no species in species_capt. adding unspecified organisms to species list in this case. 
            t3=df.loc[t1_index,'species_capt'].explode()
            t3_index=t3[t3.isna()].index
            df.loc[t3_index,'species_capt'].apply(lambda x: x.append('unspecified organisms'))
            return(df)
        
        def df_result_binarize(df,staph_bool=True):
            """ 
            mapping enumerated result_binary values into more discrete binary values (0=neg/unclear/null; 1=likely positive)
            """
            neg_binary_bool=df['pos_culture_audit1'].apply(lambda x: re.search(r'neg',str(x).lower()) is not None)
            pos_binary_bool=df['pos_culture_audit1'].apply(lambda x: re.search(r'pos',str(x).lower()) is not None)
            desc_binary_bool=df['pos_culture_audit1'].apply(lambda x: re.search(r'descriptive',str(x).lower()) is not None)

            df.loc[neg_binary_bool,'pos_culture_audit2']='negative'
            df.loc[pos_binary_bool,'pos_culture_audit2']='positive'

            df['pos_culture_audit2']= df['pos_culture_audit1'].apply(lambda x: re.split(r'[\_]?x?\d{1,}',x)[0])

            df.loc[desc_binary_bool,'pos_culture_audit2']='negative'

            if staph_bool==False: #if the staph_neg_correction boolean is negative, aka no multiple coag neg staph required for pos, then this is applied as a correction.
                staph_binary_bool=df['pos_culture_audit1'].apply(lambda x: re.search(r'staph',str(x).lower()) is not None) #including a staph 
                df.loc[staph_binary_bool,'pos_culture_audit2']='positive'

            df['pos_culture_audit2']= df['pos_culture_audit2'].apply(lambda x: re.split(r'\/null',x)[0])
            pos_bool= df['pos_culture_audit2'].apply(lambda x: re.search(r'pos',x)is not None)
            neg_bool= df['pos_culture_audit2'].apply(lambda x: re.search(r'neg',x)is not None)
            df.loc[pos_bool,'pos_culture_audit2']='positive'
            df.loc[neg_bool,'pos_culture_audit2']='negative'
            #result

            result2_mapper={
                    'negative':0,
                    'positive':1,
                    'unclear':0,
                    'not_captured':0,
                    'yeast':0,
                    'virus':0
                }

            df['pos_culture_status']= df['pos_culture_audit2'].map(result2_mapper)

            return(df)
        
        
        def add_review_suggestion_flags(df,
                                text_col):
    
            """
            attempt to add on some logical "manual review suggested" flags onto cases to reduce false positive/negative classifications. currently
            flags cases with "flora" in text, >=1 species capture, and currently classifid as negative. inspired by some challenging to classify cases in our 2d validation set. 
            """
                ### flora flag testing
            flora_bool1=df[text_col].apply(lambda x: re.search(r'flora',str(x).lower())is not None)
            flora_bool2=df['species_capt'].apply(lambda x: len(x))>0
            flora_bool3= df['pos_culture_status']==0
            flora_flag= (flora_bool1) & (flora_bool2) & (flora_bool3) 

            df['flora_flag']=0
            df.loc[flora_flag,'flora_flag']=1
            return(df)
        
        
        def OHDSI_ID_MAP(x):
            """
            function to map OHSDI concept ID based on the dictionary in OHDSI_MAP
            """
            if x in self.OHDSI_ID_DIC.keys():
                value= self.OHDSI_ID_DIC[x]
            else:
                value=999999999
            return(value)

        def OHDSI_NAME_MAP(x):
            """
            function to map OHSDI concept names based on the dictionary in OHDSI_MAP
            """
            if x in self.OHDSI_NAME_DIC.keys():
                value= self.OHDSI_NAME_DIC[x]
            else:
                value='not_OHDSI_mapped'
            return(value)

        
        def regex_list_capture(df,#: pd.core.frame.DataFrame, 
                               regex_list,#: list,
                               text_col_main,#: 'str',
                               capture_col,#: 'str',
                               regex_col,#: 'str',
                              regex_block='unspecified_regex_block',#: 'str'='unspecified_regex_block',
                              override_result=False
                              ):
            """
            function: a generalized framework to iterate through a list of regular expressions, apply them to a text column ,
            make a dataframe of rows vs regex with values = capture groups, and assign values to the 
            origional dataframe w/ the list of regex captured, and possibly list of regex groups used.

                    Parameters:
                            df (dataframe): input dataframe of microbiology notes
                            regex_list (list): regex list to iterate through with relevant captures. see regex_blocks.py for lists.
                            text_col_main (str): name of the column where microbio reports are stored (parsed if available)
                            capture_col (str): name of the column where regex captures are stored
                    kwargs:
                            regex_block (str): name of the label to add to "regex_source", to help audit the regex block responsible for infection classification.
                                NOTE: infection_estimation is sensitive to 'pos' and 'neg' labels in this column. 
                            regex_col (str): default=None, if not none, adds another column recording the raw regular xpressions with a capture hit. 
                            override_result (bool): used in the negative infection classification path to record species but not change 'result_binary'

                    Returns:
                            df (dataframe): input datafram with ['regex_text','regex_source','capture'] columns added and populated. 
            """
        ### making # of boolean lists of length df for each entry in negative regex list
            bool_list=[[False for i in range(len(df[text_col_main]))] for x in range(len(regex_list))]

            capture_df= pd.DataFrame( index=df.index, columns= regex_list)
            capture_df[capture_df.isna()]='not_captured'

            ##testing this for result binary
            capture_df2= pd.DataFrame( index=df.index, columns= regex_list)
            col_list=list(capture_df)

            for i in range(0,len(bool_list)): ## looping through the regex list and vectorizing the regex captures across all rows
                bool_list[i]=df[text_col_main].apply( lambda x: re.search(regex_list[i], str(x).lower()) != None)
                capture= df.loc[bool_list[i], text_col_main].apply( lambda x: re.search(regex_list[i], str(x).lower()).group().strip(' ')) #
                capture_df.loc[bool_list[i], col_list[i]]=capture
                capture_df2.loc[bool_list[i], col_list[i]]='{}{}'.format(regex_block, i)

                #storing pos_culture_audit1 value to overwrite it after normal operation if override==True. Written this way such that normal use doesn't incure more operations.
                if override_result==True: 
                     stored_value=df.loc[bool_list[i], 'pos_culture_audit1']

                df.loc[bool_list[i], 'pos_culture_audit1']='{}{}'.format(regex_block, i)

                if override_result==True:
                     df.loc[bool_list[i], 'pos_culture_audit1']=stored_value

                df.loc[bool_list[i], 'regex_text']=regex_list[i]
                df.loc[bool_list[i], 'regex_source']=regex_block

            df_list = capture_df.values.tolist()
            df[capture_col]=[[x for x in y if x!='not_captured'] for y in df_list]

            ### adding spot for list of regex expressions that were triggered
            if regex_col!=None:
                t=np.where(capture_df != 'not_captured', capture_df.columns,'').tolist()
                df[regex_col]= [[x for x in y if x!='']for y in t]
            return(df)
        
        
        def staph_classifier(df, coag_neg_correction,  text_col, override_result=False):
            """
            function: staphylococcus have a diverse set of bacteria with different clinical interpretations/manifestations/severity. 
            Notably, coag negative staph are common contaminants and are often required to have repeat positive cultures for a confirmed positive. this function parses text for various staph regex and assigns species, binary classification, regex used, and regex category to parsed rows. contamination_correction() can be used as a followup to change neg_staph binary results -> pos_staph if duplicate neg_staph are present. 
                    Parameters:
                            df (dataframe): input dataframe of microbiology notes
                            coag_neg_correction(bool): if the coagulase negative correction is False, all staph pickups will be pos_staph rather than the staph_classification_dic value.
                            text_col (str): column with (parsed) microbio string to be classified 

                    kwargs:
                            species_name: (str) name of extracted species column to be added.
                    Returns: 
                            df (dataframe):  input dataframe with ['regex_text','regex_source','capture'] columns populated for the various staph species. 
            """
            for element in self.staph_regex_dic.keys():
                key_bool= df[text_col].apply( lambda x: re.search(self.staph_regex_dic[element], str(x).lower()) != None)      
                df.loc[key_bool,'species_regex'].apply(lambda x:selective_append(x, element))#=element
                df.loc[key_bool,'species_capt'].apply(lambda x:selective_append(x, element))
                
                #override_result: storing pos_culture_audit1 value to overwrite it after normal operation if override==True. Written this way such that normal use doesn't incure more operations.
                #this is used to capture staph species in results classified as negative without changing the classification status.
                if override_result==True: 
                     stored_value=df.loc[key_bool, 'pos_culture_audit1']
                        
                df.loc[key_bool, 'pos_culture_audit1']=self.staph_classification_dic[element]

                if coag_neg_correction==False: ##if the coagulase negative correction if off, all staph pickups will be pos_staph rather than the staph_classification_dic value.
                     df.loc[key_bool, 'pos_culture_audit1']='pos_staph'
                if override_result==True: #storing pos_culture_audit1 value to overwrite it after normal operation if override==True. Written this way such that normal use doesn't incure more operations.
                    df.loc[key_bool, 'pos_culture_audit1']=stored_value
                df.loc[key_bool,'regex_text']=self.staph_regex_dic[element]
                df.loc[key_bool,'regex_source']='species_specific_staph' 

            #final catchall for staph without a label of other staph
            key_bool= df[text_col].apply(lambda x: (re.search(r'staph[\w]*', str(x).lower()) is not None) & (
                                                    re.search(r'epidermidis|hominis|saprophyticus|\bcoag[ulase]*\b|aureus|oxacillin|methicillin|lugdunensis', str(x).lower()) is None)) 
            df.loc[key_bool,'species_regex'].apply(lambda x:selective_append(x, 'staphylococcus_unspecified'))#=element
            df.loc[key_bool,'species_capt'].apply(lambda x:selective_append(x, 'staphylococcus_unspecified'))
            if override_result==False:
                df.loc[key_bool, 'pos_culture_audit1']='pos_staph_unspecified'
                df.loc[key_bool,'regex_text']='staph_unspecified'
                df.loc[key_bool,'regex_source']='species_specific_staph'       
            return(df)

        
        
        def contamination_correction(df, text_col, contamination_marking='neg_staph'):
            """
            function: optional function in rbmce workflow. groups df by a visit/encounter identifier and counts the # of culture_id's classified as "contamination_marking" (default negstaph from staph_classifier()). if >1, then changes the neg_staph (or other possible contamination marking) to a positive value. This is performed to mirror the practice of requiring multiple  cultures to be considered positive (to rule out contamination).  
            Currently rbmce is only setup to check for coag_negative staph contamination. 
            To scale this across other common contaminants or findings requiring two consecutive positives to = true positive, a function needs to be run prior
            to this that will apply regular expressions to identify the organisms/findings of interest and the "contamination_marking" will need to replace the value in positive_culture_audit
            
            currently this function is reliant on staph_classifier() being run before it to add "neg_staph" to pos_culture_audit1.

                    Parameters:
                            df (dataframe): input dataframe of microbiology notes
                            text_col (str): column with (parsed) microbio string to be classified 

                    kwargs:
                            contamination_marking (str): marking to put in pos_culture_audit1 if a contamination 
                    Returns: 
                            df (dataframe):  input dataframe with ['regex_text','regex_source','capture'] columns populated for the various staph species. 

            """
            many_negstaph_bool=(df.loc[df['pos_culture_audit1']==contamination_marking,:].groupby(self.visit_id_col)[self.culture_id_col].nunique()>1) 
            negstaph_vid=many_negstaph_bool[many_negstaph_bool].reset_index()[self.visit_id_col].to_list()

            df.loc[(df[self.visit_id_col].isin(negstaph_vid)) &(df['pos_culture_audit1']==contamination_marking),'pos_culture_audit1']='non_contamination_pos' #'repeat_coagN_staph_pos'
            return(df)
        
        
        def microbio_note_preprocess(data, text_col):
            """ uses value_map_dic 1 and 2 to substitute out common abbreviations and formatting to more parser friendly formatting. """

            mapped=data[text_col].map(self.value_map_dict)
              
            data.loc[mapped.notna(),text_col]=mapped[mapped.notna()]
                ###
            for element in self.value_map_dict2.keys():
                data[text_col]=self.raw_data[text_col].apply(lambda x: re.sub(element, self.value_map_dict2[element], str(x), flags=re.IGNORECASE))

            data_preprocessed=data.copy()
            data_preprocessed['pos_culture_audit1']=pd.Series(['not_captured' for x in range(len(data_preprocessed))], name='pos_culture_audit1')
            data_preprocessed['regex_source']=pd.Series(['not_captured' for x in range(len(data_preprocessed))], name='pos_culture_audit1')
            data_preprocessed['regex_text']=pd.Series(['not_captured' for x in range(len(data_preprocessed))], name='pos_culture_audit1')

            
            
            return(data_preprocessed)
        
        def rarrange_col_order(data):
            """simple function to reorder annotated_data columns in cleaner format"""
            list1=list(self.raw_data)
            list2=['pos_culture_audit1','pos_culture_audit2',
             'pos_culture_status','species_capt_all',
             'OHDSI_ID',
             'OHDSI_Concept' ]
            list12=(list1+list2)
            col_bool=[x not in list12 for x in list(data)]
            remaining_col_names=list(data.loc[:,col_bool])
            rearranged_col_names= list12+remaining_col_names

            data_out= data.loc[:,rearranged_col_names]
            return(data_out)

        ##########################  operations  ##########################
                
            
        ##instantiating attributes tied to the annotate() parameters for run auditing:
        tic_start = time.perf_counter()
    
    
        self.annotate_params={'staph_neg_correction':staph_neg_correction,
                             'specimen_col':specimen_col,
                             'review_suggestions':review_suggestions,
                             'likelyneg_block_skip':likelyneg_block_skip}
        if verbose==True:
            print('step 0: simple cleaning of parsed_note + annotation of descriptive info for specimen and quantitative information')
        
        
#         print('step0.1') 
        ########step0.1: uses value_map_dic 1 and 2 to substitute out common abbreviations and formatting to more parser friendly formatting. 

        data= microbio_note_preprocess(self.raw_data, self.text_col)
#         data=data.sort_values([self.culture_id_col, self.visit_id_col, self.text_col])
        data=data.reset_index()


#         print('step0.2') ###non-midified as of yet
        ########step0.2&0.3: parses quantitative info and specimen info when possible.
        data=regex_list_capture(data,#MicrobEx, 
                          text_col_main=self.text_col,
                        regex_list=self.quant_regex_list, 
                        capture_col='quant_descriptive_capt',
                        regex_block='quant_descriptive',
                        regex_col='quant_descriptive_regex',
                        override_result=False
              )
        
#         print('step0.3') #accounting for preexisting specimen col, and annotating specimen. note this step has not been validated adn does not impact classifications.
        if self.annotate_params['specimen_col']==None:
            specimen_col_param=self.text_col
        else:
            specimen_col_param=specimen_col

        data= regex_list_capture(data,
                        regex_list=self.specimen_regex_list,
                        text_col_main=specimen_col_param,
                        capture_col='specimen_descriptive_capt',
                        regex_block='specimen_descriptive',
                        regex_col='specimen_descriptive_regex',
                        override_result=False
              )
        
        data['specimen_descriptive_capt']= data['specimen_descriptive_capt'].apply(lambda x: [str(y).split('sample:')[-1].strip() for y in x] )
        data['specimen_descriptive_capt']= data['specimen_descriptive_capt'].apply(lambda x: [str(y).split('source:')[-1].strip() for y in x] )
        data['specimen_descriptive_capt']= data['specimen_descriptive_capt'].apply(lambda x: [str(y).split('specimen:')[-1].strip() for y in x] )      
        
          ########step1: parses blatent negative results and non-bacterial species.
        tic = time.perf_counter()
        if verbose==True:
            print('step1: parses blatent negative results and non-bacterial species.')

        ##negative captures
        data=regex_list_capture(data,#MicrobEx, 
                          text_col_main=self.text_col,
                        regex_list=self.negative_regex_list, 
                        capture_col='negative_capt',
                        regex_block='negative_classifying',
                        regex_col='negative_regex',
                        override_result=False
              )
        
        ## 11/15/21 exclding this while converting to oop.
        #accounting for cases w/ negative for and also excluding current positives just incase note says "neg for x, pos for y..."
        neg_not_pos=(data[self.text_col].apply( lambda x: re.search(r'negative for', str(x).lower()) != None) &
                (data['pos_culture_audit1'].apply(lambda x:re.search(r'pos',str(x)) != None))) #fixed, changed from is not none. 8/24
        data.loc[neg_not_pos, 'pos_culture_audit1']='negative_excluding_p'
        ##### xxx
        data.loc[neg_not_pos, 'regex_text']='negative_excluding_p'
        data.loc[neg_not_pos, 'regex_source']='negative_classifying'


        #yeast
        data= regex_list_capture(data,
                               text_col_main=self.text_col,
                             regex_list=self.yeast_regex_list,
                             capture_col='yeast_capt',
                             regex_block='negative_classifying',
                              regex_col='yeast_regex')

        #virus
        data= regex_list_capture(data,
                               text_col_main=self.text_col,
                             regex_list=self.virus_regex_list,
                             capture_col='virus_capt',
                             regex_block='negative_classifying',
                              regex_col='virus_regex')
        ##null values get an negative. 
        data.loc[data[self.text_col].isna(), 'pos_culture_audit1']='negative/null'
        data.loc[data[self.text_col].isna(),'regex_text']='negative/null'
        data.loc[data[self.text_col].isna(), 'regex_source']='negative/null'   
        
        
        toc = time.perf_counter()
        print(f"     step1 runtime: {toc - tic:0.4f} seconds")
        
        
        
        ########step2: splitting the parsed negatives out so "negative for x" type notes aren't flagged as false positives. also splits virus and yeast out as well    
        tic = time.perf_counter()
        if verbose==True:
            print('step2: negative row species captures + sequestering the negative rows from those without any capture before downstream positive annotations.')


        data, data_neg =df_split_regex(data, result_binary_regex_split=r'neg')  
        data, data_yeast =df_split_regex(data, result_binary_regex_split=r'yeast')
        data, data_virus =df_split_regex(data, result_binary_regex_split=r'virus')  

        ### combining data_neg + virus + yeast back together
        data_neg=data_neg.append(data_yeast)#df_concat(data_neg, data_yeast)
        data_neg=data_neg.append(data_virus)#data_neg=df_concat(data_neg, data_virus)

        
        
        ########step2.1: adding species captures on negatives without changing pos_culture_audit1 and pos_culture_status, aka binary outcome. 
#         tic = time.perf_counter()   
        data_neg= regex_list_capture(data_neg,
                                     self.species_regex_list,
                                     self.text_col,
                                     capture_col='species_capt',
                                     regex_block='species_positive',
                                     regex_col='species_regex', 
                                     override_result=True)
        

        data_neg= staph_classifier(df=data_neg, 
                                 coag_neg_correction=self.annotate_params['staph_neg_correction'],
                                 text_col=self.text_col,
                                 override_result=True)    



            ####8/9/21 adding rows with a yeast/virus + no negative captures + >=1 other species present. 
    #     elementwise_virusyeastlen= data_neg['yeast_capt'].apply(lambda x: len(x)).combine(data_neg['virus_capt'].apply(lambda x: len(x)), max)
        elementwise_yeastlen=data_neg['yeast_capt'].apply(lambda x: len(x))
        elementwise_viruslen=data_neg['virus_capt'].apply(lambda x: len(x))
        elementwise_virusyeastlen=pd.concat([elementwise_yeastlen, elementwise_viruslen], axis=1, sort=True).max(axis=1)

        elementwise_specieslen=data_neg['species_capt'].apply(lambda x: len(x))
        elementwise_neglen=data_neg['negative_capt'].apply(lambda x: len(x))


        exemption_cid= data_neg.loc[(elementwise_virusyeastlen>0) & (elementwise_specieslen>0) & (elementwise_neglen==0), self.culture_id_col].to_list()
        data_neg_exemption= data_neg[data_neg[self.culture_id_col].isin(exemption_cid)].copy()
        data_neg= data_neg[~data_neg[self.culture_id_col].isin(exemption_cid)].copy()

        data=data.append(data_neg_exemption)#df_concat(data, data_neg_exemption)    
        

        print('n= {} rows ({} unique cultures) added back from the neg list via virus/yeast + bacerial species exemption'.format(len(data_neg_exemption),data_neg_exemption[self.culture_id_col].nunique()))

        toc = time.perf_counter()
        print(f"     step2 runtime: {toc - tic:0.4f} seconds")

        
        ########step3: unspecific pos regex:
        tic = time.perf_counter()
        if verbose==True:
            print('step3: annotating unspecific positive rows.')
        
        data= regex_list_capture(data,
                 self.pos_quant_list,
                 self.text_col,
                 capture_col='pos_quant_capt',
                 regex_block='positive_unspecific',
                 regex_col='pos_quant_regex')
    
        data= regex_list_capture(data,
                 self.pos_qual_list,
                 self.text_col,
                 capture_col='pos_qual_capt',
                 regex_block='positive_unspecific',
                 regex_col='pos_qual_regex')


        
        toc = time.perf_counter()
        print(f"     step3 runtime: {toc - tic:0.4f} seconds")

        ########step4: specific species based pos regex:   
        tic = time.perf_counter()
        if verbose==True:
            print('step4: annotating species specific positives.')

        data= regex_list_capture(data,
                 self.species_regex_list,
                 self.text_col,
                 capture_col='species_capt',
                 regex_block='species_positive',
                 regex_col='species_regex', 
                 override_result=False)

        toc = time.perf_counter()
        print(f"     step4 runtime: {toc - tic:0.4f} seconds")

        
#         ########step5: specific staph parsings:

        tic = time.perf_counter()
        if verbose==True:
            print('step5: annotating staph positives with (optional setting) handling for coagulase negative staph; setting = {}'.format(self.annotate_params['staph_neg_correction']))
        data= staph_classifier(data,
                             coag_neg_correction=self.annotate_params['staph_neg_correction'],
                             text_col=self.text_col, 
                             override_result=False) #doing staph parsings
        if self.annotate_params['staph_neg_correction']==True:

            data= contamination_correction(data,
                                          text_col=self.text_col
                                         ) ### accounting for multiple instances of staph coag negatives or other neg staph as contaminants
            toc = time.perf_counter()
            print(f"     step5 runtime: {toc - tic:0.4f} seconds")
    

#         ########step6: final pass to categorize value col with unclear language:
        tic = time.perf_counter()
        if verbose==True:
            print('step6: annotating any previously positive row with unclear language.')       
        data= regex_list_capture(data,
             self.unclear_regex_list,
             self.text_col,
             capture_col='unclear_capt',
             regex_block='unclear',
             regex_col='unclear_regex')
        
        #part of the unclear parsing: either likely negative or more nuanced negatives (eg "no x,y,z detected")
        data= regex_list_capture(data,
             self.likely_negative_regex_list,
             self.text_col,
             capture_col='likelyneg_capt',
             regex_block='likelyneg', 
             regex_col='likelyneg_regex',
             override_result=self.annotate_params['likelyneg_block_skip']) ## i also moved the "multi-neg" instances, aka lists of no x, y, or z detected, to this for cohesion.

        data['regex_capture_quant']='not_captured'
        data.loc[data['pos_culture_audit1']=='not_captured','regex_capture_quant']= 'note not otherwise categorized'

        toc = time.perf_counter()

        ########step6.1: add unspecific_positive to species list for rows with only non-specific positive captures
        data.loc[data['pos_culture_audit1'].apply(lambda x: re.search(r'unspecific',str(x))is not None),'species_capt'].apply(lambda x: x.append('positive_unspecific'))
        print(f"     step6 runtime: {toc - tic:0.4f} seconds")

        
        if verbose==True:
            print('step7: final datastructure management, mapping species captures to OHDSI ontology, and finalizing positive culture status annotation.')

        #concating the negative classified back in (yeast+virus+neg were concatenated previously)
        data=data.append(data_neg)#df_concat(data, data_neg_exemption)    


        ### adding a unspecified organism marker for multipos cases without any specified species
        data=final_multiorg_adjustment(data)

        ###making a all virus+yeast+bacteria species captured column.
        data['species_capt_all']=data['species_capt']+data['yeast_capt']
        data['species_capt_all']=data['species_capt_all']+data['virus_capt']

        ### mapping to OHDSI
        data['OHDSI_ID']=data['species_capt_all'].apply(lambda x: [OHDSI_ID_MAP(y) for y in x])
        data['OHDSI_Concept']=data['species_capt_all'].apply(lambda x: [OHDSI_NAME_MAP(y) for y in x])

        ##binarizing parsed classification
        data=df_result_binarize(data)

        if self.annotate_params['review_suggestions']==True:
        
            data= add_review_suggestion_flags(data,
                                            text_col=self.text_col, #species_list=species_regex_list,
                                           )
            
            
            

        #forcing a sort to mirror input
        data=data.sort_values('index')
        data=data.drop(columns=['index'])

        
                ### filling in empty lists on col that were added topositive block only:
        col_list=[
            'pos_quant_capt',
            'pos_quant_regex',
            'pos_qual_capt',
            'pos_qual_regex',
            'unclear_capt',
            'unclear_regex',
            'likelyneg_capt',
            'likelyneg_regex',
            #'regex_capture_quant'
            ]

        for element in col_list:
            data[element]=data[element].fillna("").apply(list)
            
        data['regex_capture_quant']=data['regex_capture_quant'].fillna("not_captured")

        self.annotated_data=rarrange_col_order(data)
        
        print(f"     step7 runtime: {toc - tic:0.4f} seconds")

        toc_start = time.perf_counter()
        print(f"##### total runtime: {toc_start - tic_start:0.4f} seconds #####")
        
        print('Annotation Finished, see class_object.annotated_data for annotation output.')