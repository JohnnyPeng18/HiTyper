# HiTyper
![](https://img.shields.io/badge/Version-1.0-blue)



This is the tool released in the ICSE 2022 paper ["Static Inference Meets Deep Learning: A Hybrid Type InferenceApproach for Python"](https://arxiv.org/abs/2105.03595).

## Updates

**8 Aug, 2022:** 

We add a new command `hityper preprocess` to transform the json files in ManyTypes4py datasets into the `groundtruth.json` and `detailed_groundtruth.json` files HiTyper needs under `hityper eval`. 

We also add a new option `-g` in `hityper findusertype` to collect the `usertypes.json` HiTyper needs under `hityper eval` according to the groundtruth file `groundtruth.json`.

## Workflow

HiTyper is a hybrid type inference tool built upon Type Dependency Graph (TDG), the typical workflow of it is as follows:

![](https://github.com/JohnnyPeng18/HiTyper/blob/main/imgs/workflow.png)

For more details, please refer to the [paper](https://arxiv.org/abs/2105.03595).

## Methdology

The general methdology of HiTyper is:

1) Static inference is accurate but suffer from coverage problem due to dynamic features

2) Deep learning models are feature-agnostic but they can hardly maintain the type correctness and are unable to predict unseen user-defined types

The combination of static inference and deep learning shall complement each other and improve the coverage while maintaining the accuracy.

## Install

To use HiTyper on your own computer, you can build from source: (If you need to modify the source code of HiTyper, please use this method and re-run the `pip install .` after modification each time)

```sh
git clone https://github.com/JohnnyPeng18/HiTyper.git && cd HiTyper
pip install .
```

**Requirements:**

- Python>=3.9
- Linux

HiTyper requires running under Python >= 3.9 because there are a lot of new nodes introduced on AST from Python 3.9. However, HiTyper can analyze most files written under Python 3 since Python's AST is backward compatible.

You are recommended to use `Anaconda` to create a clean Python 3.9 environment and avoid most dependency conflicts:

````sh
conda create -n hityper python=3.9
````

## Usage

Currently HiTyper has the following command line options: (Some important settings are stored in file `config.py`, you may need to modify it before running HiTyper)

### findusertype

```sh
usage: hityper findusertype [-h] [-s SOURCE] [-p REPO] [-g GROUNDTRUTH] [-c CORE] [-v] [-d OUTPUT_DIRECTORY]

optional arguments:
  -h, --help            show this help message and exit
  -s SOURCE, --source SOURCE
                        Path to a Python source file
  -p REPO, --repo REPO  Path to a Python project
  -g GROUNDTRUTH, --groundtruth GROUNDTRUTH
                        Path to a ground truth file
  -c CORE, --core CORE  Number of cores to use when collecting user-defined types
  -v, --validate        Validate the imported user-defined types by finding their implementations
  -d OUTPUT_DIRECTORY, --output_directory OUTPUT_DIRECTORY
                        Path to the store the usertypes
```

**Example of collecting user-defined types in source files:**

```sh
hityper findusertype -s python_project_repo/test.py -p python_project_repo -v -d outputs
```

*This command generates the user-defined types collected by HiTyper and save them as `.json` files under `outputs/` folder.*

`-p` option is required here, if you do not specify `-s`, the HiTyper will collect user-defined types in all files of repo specified by `-p`.

**[Newly Added 6 Aug]**

We add a option to automatically generate all user-defined type files that a ground truth dataset needs to evaluate HiTyper.

**Example of collecting user-defined types in groundtruth datasets:**

```sh
hityper findusertype -g groundtruth.json -p repo_prefix -c 60 -d outputs
```

*This command generates the user-defined types in files indicates by `groundtruth.json` collected by HiTyper and save them as `.json` files under `outputs/` folder.*

For the `groundtruth.json`, you need to use the same file in `hityper eval` command or generate it by using `hityper preprocess` command.

`-p repo_prefix` is an optional argument here, if the filenames in `groundtruth.json` are the absolute paths then you do not need to specify `-p`, otherwise use `-p` to indicate which folder the source files are stored.

The collection of all user-defined types for a large dataset is quite slow, try to specify a large number of cores used to make this process faster.

### gentdg

```sh
hityper gentdg [-h] [-s SOURCE] -p REPO [-o] [-l LOCATION] [-a] [-c] [-d OUTPUT_DIRECTORY] [-f {json,pdf}]

optional arguments:
  -h, --help            show this help message and exit
  -s SOURCE, --source SOURCE
                        Path to a Python source file
  -p REPO, --repo REPO  Path to a Python project
  -o, --optimize        Remove redundant nodes in TDG
  -l LOCATION, --location LOCATION
                        Generate TDG for a specific function
  -a, --alias_analysis  Generate alias graphs along with TDG
  -c, --call_analysis   Generate call graphs along with TDG
  -d OUTPUT_DIRECTORY, --output_directory OUTPUT_DIRECTORY
                        Path to the generated TDGs
  -f {json,pdf}, --output_format {json,pdf}
                        Formats of output TDGs
```

**Example:**

```
hityper gentdg -s python_project_repo/test.py -p python_project_repo -d outputs -f json -o
```

*This command generates the TDG for all functions in file `python_project_repo/test.py` and save them into `outputs` folder.* 

Note that if you choose `json` format to save TDG, it will be only ONE `json` file that contains all TDGs in the source file. However, if you choose `pdf` format to save TDG, then there will be multiple `pdf` files and each one correspond to one function in the source file. This is because a pdf file can hardly contain a large TDG for every functions.

For the location indicated by `-l`, use the format `funcname@classname` and use `global` as the classname if the function is a global function.

HiTyper uses [PyCG](https://github.com/vitsalis/PyCG) to build call graphs in call analysis. Alias analysis and call analysis are temporarily built-in but HiTyper does not use them in inference. Further updates about them will be involved in HiTyper. 

### infer

```sh
hityper infer [-h] [-s SOURCE] -p REPO [-l LOCATION] [-d OUTPUT_DIRECTORY] [-m RECOMMENDATIONS] [-t] [-n TOPN]

optional arguments:
  -h, --help            show this help message and exit
  -s SOURCE, --source SOURCE
                        Path to a Python source file
  -p REPO, --repo REPO  Path to a Python project
  -l LOCATION, --location LOCATION
                        Type inference for a specific function
  -d OUTPUT_DIRECTORY, --output_directory OUTPUT_DIRECTORY
                        Path to the generated TDGs
  -m RECOMMENDATIONS, --recommendations RECOMMENDATIONS
                        Path to the recommendations generated by a DL model
  -t, --type4py         Use Type4Py as the recommendation model
  -n TOPN, --topn TOPN  Indicate the top n predictions from DL models used by HiTyper
```

**Example:**

```
hityper infer -s python_project_repo/test.py -p python_project_repo -d outputs -n 1 -t 
```

*This command generates the inferred types for all variables, arguments and return values in the source file and save them into `output` folder.*

If you do not specify `-m` or `-t` option, then HiTyper will only use the static inference part to infer types. Static inference generally takes several minutes.

For the location indicated by `-l`, use the format `funcname@classname` and use `global` as the classname if the function is a global function.

**Recommendation Model:**

Note that HiTyper natively supports the recommendations from Type4Py and it invokes the following API provided by Type4Py to get recommendations if you use option `-t`:

```
https://type4py.com/api/predict?tc=0
```

**This will upload your file to the Type4Py server!** If you do not want to upload your file, you can use the [docker](https://github.com/saltudelft/type4py/wiki/Using-Type4Py-Rest-API) provided by Type4Py and changes the API in `config.py` into:

```
http://localhost:PORT/api/predict?tc=0
```

According to our experiments, the Type4Py model has much lower performance by quering the API above, you are suggested to train the model locally and generate the recommendation file which can be passed to `-m`.

**Note: HiTyper's performance deeply depends on the maximum performance of recommendation model (especially the performance to predict argument types). Type inference of HiTyper can fail if the recommendation model cannot give a valid prediction while static inference does not work!** 

If you want to use another more powerful model, you write code like `__main__.py` to adapt HiTyper to your DL model.

### eval

```sh
hityper eval [-h] -g GROUNDTRUTH -c CLASSIFIED_GROUNDTRUTH -u USERTYPE [-m RECOMMENDATIONS] [-t] [-n TOPN]

optional arguments:
  -h, --help            show this help message and exit
  -g GROUNDTRUTH, --groundtruth GROUNDTRUTH
                        Path to a ground truth dataset
  -c CLASSIFIED_GROUNDTRUTH, --classified_groundtruth CLASSIFIED_GROUNDTRUTH
                        Path to a classified ground truth dataset
  -u USERTYPE, --usertype USERTYPE
                        Path to a previously collected user-defined type set
  -m RECOMMENDATIONS, --recommendations RECOMMENDATIONS
                        Path to the recommendations generated by a DL model
  -t, --type4py         Use Type4Py as the recommendation model
  -n TOPN, --topn TOPN  Indicate the top n predictions from DL models used by HiTyper
```

**Example:**

```sh
hityper eval -g groundtruth.json -c detailed_groundtruth.json -u usertypes.json -n 1 -t
```

*This command evaluates the performance of HiTyper on a pre-defined groundtruth dataset. It will output similar results like stated in `Experiment Results` part.*

Before evaluating Hityper using this command, please use `hityper findusertype` command to generate `usertypes.json`. This typically takes several hours, depending on the number of files.

This option is designed only for future research evaluation.

### Preprocess

```sh
usage: hityper preprocess [-h] -p JSON_REPO [-d OUTPUT_DIRECTORY]

optional arguments:
  -h, --help            show this help message and exit
  -p JSON_REPO, --json_repo JSON_REPO
                        Path to the repo of JSON files
  -d OUTPUT_DIRECTORY, --output_directory OUTPUT_DIRECTORY
                        Path to the transformed datasets
```

**Example:**

```sh
hityper preprocess -p ManyTypes4PyDataset/processed_projects_complete -d outputs
```

*This command transforms the json files in ManyTypes4Py datasets into the `groundtruth.json` and `detailed_groundtruth.json` files that required by the `hityper eval` command.*

This command is to facilitate the researchers that use ManyTypes4Py dataset and want to evaluate HiTyper in it.

If you want to run HiTyper in other datasets, please follow the same logic in `transformDataset` function of  `HiTyper/hityper/utils.py` to write a script.

## Experiment Results

**Dataset:**

The following results are evaluated using the [ManyTypes4Py](https://zenodo.org/record/4719447#.YjxcpBNBxb8) dataset. 

Since the original dataset does not contain Python source files, to facilitate future research, we here also attached a [link](https://drive.google.com/file/d/1HdZyd3dKAUkiv2Nl0Zynp_YhrqU6HfMx/view?usp=sharing) for the Python source files HiTyper uses to infer types. Attached dataset is not identical with the original one because the original one contains some GitHub repos that do not allow open access or have been deleted.

Note that as stated in the paper, there exists few cases (such as subtypes and same types with different names) that HiTyper should be correct but still counted as wrong in the evaluation process.

**Metrics:**

For the definition of metrics used here, please also refer to the paper. These metrics can be regarded as a kind of "recall", which evaluates the coverage of HiTyper on a specific dataset. We do not show the "precision" here as HiTyper only outputs results when it does not observe any violations with current typing rules and TDG.

**Only using the static inference part:**

| Category           | Exact Match | Match to Parametric | Partial Match |
| ------------------ | ----------- | ------------------- | ------------- |
| Simple Types       | 59.00%      | 59.47%              | 62.15%        |
| Generic Types      | 55.50%      | 69.68%              | 71.90%        |
| User-defined Types | 40.40%      | 40.40%              | 44.30%        |
| Arguments          | 7.65%       | 8.05%               | 14.39%        |
| Return Values      | 58.71%      | 64.61%              | 69.06%        |
| Local Variables    | 61.56%      | 65.66%              | 67.05%        |

You can use the following command to reproduce the above results:

```sh
hityper eval -g ManyTypes4Py_gts_test_verified.json -c ManyTypes4Py_gts_test_verified_detailed.json -u ManyTypes4Py_test_usertypes.json 
```

We do not show the performance of HiTyper integrating different DL models here since there are many factors impacting the performance of DL models such as datasets, hyper-parameters, etc. Please align the performance by yourself before utilizing recommendations from DL models.

What's more, we are currently working on building a DL model that's more suitable for HiTyper. Stay tuned!

**Other datasets:**

If you want to evaluate HiTyper on other datasets, please generate files with the same format with `ManyTypes4Py_gts_test_verified.json`, `ManyTypes4Py_gts_test_verified_detailed.json`, or you can modify the code in `__main__.py`. To check a type's category, you can use `hityper.typeobject.TypeObject.checkType()`.

In any case, you must also prepare the source files for static analysis.

**Old results:**

If you want the exact experiment results stated in the paper, please download them at this [link](https://drive.google.com/file/d/1zFVStp085bfv8WU7UCk9pIE2HEEf-CUh/view?usp=sharing).

## Todo

- Add supports for inter-procedural analysis
- Add supports for types from third-party modules
- Add supports for external function calls
- Add supports for stub files

## Cite Us

If you use HiTyper in your research, please cite us:

```latex
@inproceedings{peng22hityper,
author = {Peng, Yun and Gao, Cuiyun and Li, Zongjie and Gao, Bowei and Lo, David and Zhang, Qirun and Lyu, Michael},
title = {Static Inference Meets Deep Learning: A Hybrid Type Inference Approach for Python},
year = {2022},
isbn = {9781450392211},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3510003.3510038},
doi = {10.1145/3510003.3510038},
booktitle = {Proceedings of the 44th International Conference on Software Engineering},
pages = {2019–2030},
numpages = {12},
location = {Pittsburgh, Pennsylvania},
series = {ICSE '22}
}
```

## Contact

We actively maintain this project and welcome contributions. 

If you have any question, please contact research@yunpeng.work.

