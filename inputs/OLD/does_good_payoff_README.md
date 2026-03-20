When does compensation predict performance?
==============================


Project Overview:
------------
An investigation of the relationship between performance and compensation in three domains: Business, Sports, and Higher-Education.

Link to [Project Proposal Presentation](https://docs.google.com/presentation/d/1dIv9I93-ZDyljG-Iqil9szkqyVukK0v_kfAaxVQCIlk/edit?usp=sharing)


#### Publicly Available Data:

Link to [Urban Institute's data explorer](https://educationdata.urban.org/data-explorer/colleges/) (super cool). 

Link to [my document](https://github.com/dagny099/does_good_payoff/blob/master/docs/getting-started.rst) showing selection criteria and variables chosen.

*Rounds of downloads* <br>
Rd_1: TX, FL         ... Approximate results: 188k records from 838 institutions <br>
Rd_2: OR, AZ, MI, OH ... Approximate results: 169k records from 752 institutions <br>
Rd_3: NY, GA, MN     ... Approximate results: 170k records from 755 institutions <br>
Rd_4: CA             ... Approximate results: 164k records from 729 institutions <br>
Rd_5: VA, PA, IN, WI ... Approximate results: 178k records from 791 institutions <br>

Rationale behind states chosen:
- Question of interest is geared towards public funding and higher education outcomes
- Wikipedia lists the Top 10 university campuses by enrollment, by year

Manually summed size of aggregated csv files: **70MB**



Project Organization
------------

    ├── LICENSE
    ├── Makefile           <- Makefile with commands like `make data` or `make train`
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries
    │
    ├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
    │                         the creator's initials, and a short `-` delimited description, e.g.
    │                         `1.0-jqp-initial-data-exploration`.
    │
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    │
    ├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
    │                         generated with `pip freeze > requirements.txt`
    │
    ├── setup.py           <- makes project pip installable (pip install -e .) so src can be imported
    ├── src                <- Source code for use in this project.
    │   ├── __init__.py    <- Makes src a Python module
    │   │
    │   ├── data           <- Scripts to download or generate data
    │   │   └── make_dataset.py
    │   │
    │   ├── features       <- Scripts to turn raw data into features for modeling
    │   │   └── build_features.py
    │   │
    │   ├── models         <- Scripts to train models and then use trained models to make
    │   │   │                 predictions
    │   │   ├── predict_model.py
    │   │   └── train_model.py
    │   │
    │   └── visualization  <- Scripts to create exploratory and results oriented visualizations
    │       └── visualize.py
    │
    └── tox.ini            <- tox file with settings for running tox; see tox.readthedocs.io


--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
