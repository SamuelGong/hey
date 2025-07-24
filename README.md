# Hey

<p align="center">
    <a href="https://github.com/SamuelGong/Hey/blob/main/LICENSE"><img src="https://img.shields.io/github/license/SamuelGong/ZhihuAgent?color=yellow" alt="License"></a>
</p>

> Other languages: [中文](./README_ZH_CN.md)

This is a general-purpose AI agent designed for command-line usage, built from the ground up, 
with the exception of some optionally used MCP tools adapted from other open-source projects.
t has been tested and confirmed to run on both macOS and Linux.

<img width="2240" height="1648" alt="arch-chinese" src="https://github.com/SamuelGong/hey/blob/main/doc/arch-en.png" />

## 1. Preparation

### 1.1 Python Environment Setup
```bash
conda create -n hey python=3.10 -y
conda activate hey
pip install -e .
```

Additionally, install the IPython kernel with:

```bash
python -m ipykernel install --user
```

### 1.2 IPC Solution

Run Redis server in the background (for Inter-Process Communication) using:

```bash
# With root privileges
bash install_redis_server.sh
nohup redis-server &

# Alternative without root access:
# cd ..  # or elsewhere you want
# wget https://download.redis.io/releases/redis-7.0.15.tar.gz
# tar -xf redis-7.0.15.tar.gz
# cd redis-7.0.15
# make
# cd src
# ./redis-server &
#
# Reference: https://techmonger.github.io/40/redis-without-root/
```

[//]: # (### 1.3 MCP Server)

[//]: # ()
[//]: # (Run the native MCP server in the background &#40;for built-in tools functionality&#41;:)

[//]: # ()
[//]: # (```bash)

[//]: # (nohup python hey/mcp_tools/server.py &)

[//]: # (```)

### 1.3 Configuration

Configure your LLM API settings:
```bash
cp .env_template .env
vim .env  # for access key
cp config.yml_template config.yml
vim config.yml  # for LLM types and many others
```

### 1.4 Network Proxy Configuration

Remember to set up your terminal proxy if required (in case you can neither do Google Search nor software downloading).

## 2. Demonstration Examples

These examples showcase `hey`'s capabilities - the possibilities are only limited by your imagination.

### 2.1 Text File Operations

```bash
hey "Copy any text file located in the examples/doc directory that contains the theword 'agent' to a new folder named 'examples/new_doc'."
```

**Expected result**:
- Before: In the folder `./examples/` there is no sub-folder named `new_doc`.
- After: In the folder `./examples/` there is a sub-folder `new_doc` which contains four files: `1.txt`, `2.txt`, `3.txt`, and `4.txt`.

### 2.2 Excel File Processing

```bash
hey "Copy the 'Sheet1' Product column of the file ./examples/Invoices.xlsx to 'Sheet2' and sort 'Sheet2''s Product column in ascending order."
```

**Expected result**:
- Before: In the file `./examples/Invoices.xlsx` there is no sheet named `Sheet2`.
- After: In the file `./examples/Invoices.xlsx` there is a sheet which has the name `Sheet2` and contains only one column titled `Product`.
 From the top to the bottom cell of the column, there should be three `Alpine`, four `Carlota`, five `Majestic`, and four `quad`.

### 2.3 Interactive Task Clarification

```bash
hey "I have a task..."
# Could you please tell me the specific details of the task? For example, is it related to code development, system configuration, or something else?
# Your input (press Enter to indicate the end) >> 
I want to know lines of code in every Python file under this directory, recursively. Please save the result in ./examples/line_count.txt
```

**Expected result**:
- Before: In the file `./examples` there is no file named `line_count.txt`.
- After: In the file `./examples` there is a file named `line_count.txt` with statistics about the lines of code of every Python files in this project.

### 2.4 DeepSeek R1 Model Deployment

```bash
hey "Search to learn how to locally deploy deepseek-r1:1.5b on my machine using ollama and try to serve it in a background process so that another process can use it with Python library openai."
```

**Expected result**:
- Before: In a separate shell, `python examples/test_deepseek.py` cannot be successfully executed but raise `openai.APIConnectionError: Connection error.`.
- After: In a separate shell, `python examples/test_deepseek.py` can be successfully executed and one can see a greeting from the deployed model as the output like:
 ```
<think>

</think>

Hello! How can I assist you today? 😊
  ```

*Note: `examples/test_deepseek.py` simply connects to ollama's server and sends a "Hello" message to the `deepseek-r1:7b` model for validation.*

## 3. For developers

After code changes, always run this command in the project directory:

```bash
pip uninstall hey -y && pip cache remove hey && pip install -e .
```

## Contact

If you need any help, please submit a Github issue, or contact Zhifeng Jiang via zjiangaj@connect.ust.hk.
