<h1 align="center">

</h1>
<p>
<img alt="Version" src="https://img.shields.io/badge/version-0.0.2-blue.svg?cacheSeconds=2592000" />
<a href="https://github.com/pedroermarinho/markdown-readme-generator#readme" target="_blank"><img alt="Documentation" src="https://img.shields.io/badge/documentation-yes-brightgreen.svg" /></a>
<a href="https://github.com/pedroermarinho/markdown-readme-generator/graphs/commit-activity" target="_blank"><img alt="Maintenance" src="https://img.shields.io/badge/Maintained%3F-yes-green.svg" /></a>
<a href="https://github.com/pedroermarinho/markdown-readme-generator/blob/master/LICENSE" target="_blank"><img alt="License:MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" /></a>

</p>

### MicrobEx (Microbiology Concept Extractor):
>This code was developed to provide an open-source python package to extract clinical concepts from free-text semi-structured microbiology reports. The two primary outputs for this package are (1) an binary estimation of patient bacterial infection status and (2) a list of all clinically relevant microorganisms found in the report. These outputs were validated on two independent datasets and achieved f-1 scores over 0.95 on both outputs when compared to expert review. Full details on background, algorithm, and validation results can be seen at our paper here: (currently being written, will update once submitted to archive).

### 🏠 [Homepage](https://github.com/geickelb/microbex)
### ✨ [package](https://pypi.org/project/microbex/)

## Requirements
```sh
* python >=3.6.8
* pandas >=0.25.0

```

## Install
```sh
pip install microbex
```

## Usage

#### instantiation:
   def __init__(self, 
                 data: pd.core.frame.DataFrame, ###check if this requirement works. can work on this late.
                 text_col: str, #previously text_col_main
                 culture_id_col: str, #previously culture_id_main
                 visit_id_col: str, #previously visit_id_main
                ):

the microbex class instantiation takes in a pandas dataframe with 3 expected columns (colnames are provided as kwargs): 

* parsed_note (kwarg: text_col): 
    * microbiology report txt in either a raw or (**perferable) chopped up into components (eg gram stain/growth report/ab susceptability)
* culture_id (kwarg: culture_id_col): 
    * a primary key tied to a given sample/specimen + microbiological exam order. 
    * Often a microbiology order can be tied to numerous components (eg gram stain/growth report/ ab susceptability). additionally these can be appended to same report or added as a new report tied to same sample + order. all of these tied to a sample+order should share same culture_id
* visit_id (kwarg: visit_id_col):
    * primary key for patient's visit/encounter
    * can be 1-many:1 to culture_id or 1:1 (in which case can specify as culture_id)
    * in some datasets a patient may have multiple cultures performed in a visit/encounter. 



#### Inline:
```sh
import microbex
d={'parsed_note': 'No Salmonella, Shigella, Campylobacter, Aeromonas or Plesiomonas isolated.', 'culture_id': 1, 'visit_id': 1}
df=pd.DataFrame(data=d, index=[1])

obj1= microbex(df,
              text_col='parsed_note',
              culture_id_col='culture_id',
              visit_id_col='visit_id')

## see microbex.annotate() docstring for description of kwargs
obj1.annotate(staph_neg_correction=False, 
              specimen_col=None,
              review_suggestions=False,
              likelyneg_block_skip=False
             )

print(obj1.annotated_data.head())

obj1.annotated_data.to_pickle("<designated_save_path>'.pkl")
#note: while annotated_data can be saved as a csv, there are some columns which are made of lists in each cell. the formatting of these can sometimes not interpreted correctly.
## pkl files preserve dtype and resolve this issue. 
```


## Run tests
#### commandline 
* this test compares a freshly annotated sample_dataset with an imported pre-annotated expected version. 
```sh
cd microbex
pytest -v

```



## Author
👤 **Garrett Eickelberg**







## 🤝 Contributing
Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/geickelb/rbmce/issues). You can also take a look at the [contributing guide](https://github.com/pedroermarinho/markdown-readme-generator/blob/master/CONTRIBUTING.md)
## Show your support
Give a ⭐️ if this project helped you!
## Credits
**[Markdown Readme Generator](https://github.com/pedroermarinho/markdown-readme-generator)**
## 📝 License

This project is [MIT](https://github.com/geickelb/rbmce/blob/main/LICENSE.txt) licensed.

---
_This README was created with the [markdown-readme-generator](https://github.com/pedroermarinho/markdown-readme-generator)_