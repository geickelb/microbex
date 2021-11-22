
# utils.regex_blocks list and dictionary descriptions:
regex blocks holds numerous lists of regular expressions and dictionaries used throughout the rbmce.run() algorithm. These regular expression lists contain regular expressions designed for concept matching (often referred to as capture in this document). 
In general, these compiled regular expression lists are the engine of the algorithm. In order to tailor RBMCE to an institution's dataset, often additional regular expressions will need to be added to certain lists to capture the desired pattern. Rarely, if a regular expression in a list is causing large-scale problems not addressable in post-processing, a specific regular expression may need to be commented out. 
The regular expression lists are categorized by their desired capture theme (e.g. a unspecific positive: a bacteria positive culture that doesn't list a specific bacteria name.). the rbmce.run() algorithm runs each of these lists in a specific order and classifies bacterial positive status based on hierarichal logic (see figure 1.). 





# Microbex.annotate() bacteria positive classification logic flow:

In general the logic uesd to classify bacteria positive status is as follows:
* a Microbex object is instantiated with a df with a microbiology note, culture_id, and visit_id per row
* a Microbex object is annotated using the .annotate() class method. see documentation for parameter info.
* descriptive regex lists capture information that is annotated on the corresponding case, but doesn't affect bacterial positive classification. (eg non-descript quantitative information, specimen type, etc...)
* Next, regular expressions in the negative_regex_list are applied in order to capture cases that are clearly negative for bacterial positive status. 
    * e.g. "no infection detected"
* Next, cases with and without a negative regex capture are sequestered from one another.
* for cases with a negative capture, the collection of species_specific regular expression lists are applied to all negative cases. these include lists for yeast, common virus, and bacteria (with a specific collection of lists for staph to accomodate coagulase negative vs positive). 
    * if a case is found to have: a negative capture, yeast and or virus capture, and >=1 bacteria capture, the case is joined to the cases without any negative capture.
    * this is performed to help address false negatives of the form: "no yeast detected, staphylococcus detected".
    * all cases remaining in this negative capture group will have bacteria status classification = 0 (negative). 
* for cases without negative captures, they are passed into the "positive capture block". In this block, lists of increasingly specific regular expressions are applied to the case. 
    * First, unspecific_positive, then quantitative_positive, then species_specific positive, then staphylococcus specific positive (seperates coagulase negative vs positive), and finally some correction adjustment lists: unclear_positive and likely_negative. 
    * The goal of this is to have the latest capture be the most specific relating to positive. Once the most specific positives are captured, the correction lists look for language that might have triggered false positives, or might not have been captured yet. (e.g: indeterminent; cannot be ruled out; culture in progress).
        * the likely_negative list has an option in the run() function to be included as it can sometimes trigger false negatives. these look for certain words we found to be more likely associated with false positives, such as : "few bacteria seen". 
* finally, all positive block cases with either an unclear, likely_negative capture, or no capture at all are classified as bacteria status 0(negative)
* all other cases with a positive regex capture are classified as bacteria status= 1 (positive )


# rbmce.run() output column descriptions:

In the RBMCE output dataframe, each of the regular expressions captured by their associated lists or blocks are annotated in a specified column for easier auditing. A column title with "capt" in it will present the text captured by the regular expression, while a column title with "regex" will present the raw regular expression used to capture the capt text. The associated columns are as follows in the format {block_name: [column names]}


unspecific_positives: [pos_qual_capt,pos_qual_regex, pos_quant_capt,pos_quant_regex]

descriptives:[quant_descriptive_capt,quant_descriptive_regex, specimen_descriptive_capt, specimen_descriptive_regex]

virus and yeast species capture: [virus_capt, virus_regex, yeast_capt,yeast_regex]

bacteria species specific captures (on both positive and negative cases): [species_capt,species_regex]
    * note: cases with negative capture still have species extract performed, a species present here does not necessarily indicate bacteria status = positive.

ALL species collection (concat of bacteria + virus + yeast): [species_capt_all]

unclear and likely-negative false positive correction blocks: [unclear_capt, unclear_regex, likelyneg_capt,likelyneg_regex]

virus and yeast species capture: [virus_capt, virus_regex, yeast_capt,yeast_regex]

the following columns contain the corresponding capture used to make the bacteria positive classification. this is purely for debugging, as this information is available in other capture columns:
[regex_capture,regex_capture_quant,regex_capture_specimen,regex_source, regex_text, pos_culture_status, pos_culture_audit1,pos_culture_audit2]

columns used for regex block -> classification accounting: [pos_culture_audit1,pos_culture_audit2]
* pos_culture_status= final bacteria positive status classification. 
* pos_culture_audit1, pos_culture_audit2 start with the granular detail of which regex blocks were used to make classification. pos_culture_audit1 shows the regex index used to make a classification, which pos_culture_audit2 shows broad regex block categories. pos_culture_audit2 is directly mapped to result_num via dictionary. 


OHDSI concept mapping (can be used to map to SNOMED): [OHDSI_ID, OHDSI_Concept]


flora_flag: depreciated, will be removed in future versions. 
