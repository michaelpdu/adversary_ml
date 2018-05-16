# Adversary-Machine-Learning
Adversary Machine Learning project for experiment

## Install packages

Install following packages in pip2/pip3

```
sudo pip3 install numpy
sudo pip3 install xgboost
sudo pip3 install lief
```

Install Wine, you could refer to [https://wiki.winehq.org/Ubuntu](https://wiki.winehq.org/Ubuntu)

## Interface Description

### automation tool

#### start_ga.py
In start_ga.py, it supports JavaScript and PE adversary process. More detailed information, please refer to following Usage.

```
Usage:
    (a) find bypassed script sample
        >> python start_ga.py --file-type JS --file-path malicious_script --dna DNA_dir --start start_index --step DNA_size
        e.g.
        >> python start_ga.py --file-type JS --file-path samples/mal_script/0a0b692133dbba549c81dec49e1ba2ccf1b2bfea --dna DNA_JS/function_snippets --start 0 --step 32
      OR
    (b) find bypassed PE sample
        >> python3 start_ga.py --file-type PE --file-path malicious_pe --dna DNA_dir --start start_index --step DNA_size --tool housecallx_dir
        e.g.
        >> python3 start_ga.py --file-type PE --file-path samples/mal_pe/6d3e5e56984a7e91c7a8c434224b73886d413d1d1f435358f40bf78c71c1932d --dna DNA_PE/section_add --start 64 --step 32 --tool housecallx
```

Before PE adversarial process, it's necessary to startup cuckoo sandbox. Please refer to following instructions:

- startup VirtualBox and VMs
- startup Cuckoo Sandbox (use command 'cuckoo community' to load Cuckoo Signatures)

For more details, please refer to Cuckoo Sandbox: https://cuckoo.sh/docs/index.html

#### start_bruteforce.py
After refactoring, we add new entry and UT code in automation. New entry is workflow.py:
```
Usage:
    python3 start_bruteforce.py
```

**Anytime before submiting code, please run UT firstly!!!**

```
Usage:
    python3 ut.py
```

## Utility Tools

### generate JS function DNA files

This tool could analyze JavaScript files and dump all of function snippets.

``` python
Usage:
    python function_analyzer.py target dest_dir
```

This function will analyze target(folder or file), and generate many function files.

### generate PE section DNA files

In pe_modifier folder, there is a script to generate PE section DNA files.

```
Usage:
    python create_sections_dna.py PE_target_path dest_path
```

