# Hey

<p align="center">
    <a href="https://github.com/SamuelGong/Hey/blob/main/LICENSE"><img src="https://img.shields.io/github/license/SamuelGong/ZhihuAgent?color=yellow" alt="License"></a>
</p>

> 作者注：这份文档由 DeepSeek 从[英文原本](README.md)翻译而成。任何地方如果与原本有冲突，以原本为准。

这是一款通用型 AI 智能体，专为命令行使用而设计。
它从零开始构建，仅部分可选的 MCP 工具是由其他开源项目的成果改造而来。
该智能体已在 macOS 和 Linux 系统上测试通过，能够正常运行。

<img width="2240" height="1648" alt="arch-chinese" src="https://github.com/SamuelGong/hey/blob/main/doc/arch-ch.png" />

## 1. 准备工作

### 1.1 Python环境配置
```bash
conda create -n hey python=3.10 -y
conda activate hey
pip install -e .
```

额外安装IPython内核：
```bash
python -m ipykernel install --user
```

### 1.2 进程间通信方案

后台运行Redis服务器（用于进程间通信）：
```bash
# 拥有root权限时
bash install_redis_server.sh
nohup redis-server &

# 无root权限替代方案：
# cd ..  # 或任意目标目录
# wget https://download.redis.io/releases/redis-7.0.15.tar.gz
# tar -xf redis-7.0.15.tar.gz
# cd redis-7.0.15
# make
# cd src
# ./redis-server &
#
# 参考：https://techmonger.github.io/40/redis-without-root/
```

[//]: # (### 1.3 MCP服务器部署)

[//]: # ()
[//]: # (后台运行原生MCP服务器（使智能体能够使用内置工具）：)

[//]: # (```bash)

[//]: # (nohup python hey/mcp_tools/native/server.py &)

[//]: # (```)

### 1.3 配置文件

设置LLM API参数：
```bash
cp .env_template .env
vim .env  # 填写访问密钥
cp config.yml_template config.yml
vim config.yml  # 配置LLM类型及其他参数
```

### 1.4 网络代理

必要时请配置终端代理（否则您的智能体可能无法使用谷歌搜索或下载新的软件包）。

## 2. 功能示例

以下案例仅展示`hey`的部分能力，实际应用范围仅受您的想象力限制。

### 2.1 文本文件操作

```bash
hey "Copy any text file located in the examples/doc directory that contains the theword 'agent' to a new folder named 'examples/new_doc'."
# hey "复制examples/doc目录下所有包含'agent'的文本文件到新建的examples/new_doc目录"
```

**预期结果**：
- 初始状态：`./examples/`下无`new_doc`子目录
- 最终状态：`./examples/new_doc`目录包含四个文件：`1.txt`、`2.txt`、`3.txt`和`4.txt`

### 2.2 Excel文件处理

```bash
hey "Copy the 'Sheet1' Product column of the file ./examples/Invoices.xlsx to 'Sheet2' and sort 'Sheet2''s Product column in ascending order."
# hey "将文件./examples/Invoices.xlsx中Sheet1的Product列复制到Sheet2，并将Sheet2的Product列按升序排序"
```

**预期结果**：
- 初始状态：`./examples/Invoices.xlsx`中不存在Sheet2
- 最终状态：Sheet2包含单列Product，从上至下依次为：
  - 3个Alpine
  - 4个Carlota
  - 5个Majestic
  - 4个quad

### 2.3 交互式任务理解

```bash
hey "I have a task..."
# Could you please tell me the specific details of the task? For example, is it related to code development, system configuration, or something else?
# Your input (press Enter to indicate the end) >> 
I want to know lines of code in every Python file under this directory, recursively. Please save the result in ./examples/line_count.txt

# hey "我有一个任务..."
## 请说明任务具体细节？例如：代码开发、系统配置等
## 请输入（按Enter结束）>> 
# 我需要统计本目录（含子目录）所有Python文件的行数，结果保存到examples/line_count.txt
```

**预期结果**：
- 初始状态：`./examples`下无`line_count.txt`文件
- 最终状态：`line_count.txt`包含本项目所有Python文件的代码行数统计

### 2.4 DeepSeek R1模型部署

```bash
hey "Search to learn how to locally deploy deepseek-r1:1.5b on my machine using ollama and try to serve it in a background process so that another process can use it with Python library openai."
# hey "研究如何通过ollama在本地机器部署deepseek-r1:1.5b，并设为后台进程供Python的openai库调用"
```

**预期结果**：
- 初始状态：`python examples/test_deepseek.py`执行失败并报错`openai.APIConnectionError`
- 最终状态：`python examples/test_deepseek.py`成功执行并输出模型响应：
```
<think>

</think>

Hello! How can I assist you today? 😊
```

*注：`examples/test_deepseek.py`仅用于连接ollama服务并向`deepseek-r1:7b`模型发送"Hello"进行验证*

## 3. 开发者须知

代码修改后，请在项目目录执行以下命令：

```bash
pip uninstall hey -y && pip cache remove hey && pip install -e .
```

## 联系方式

如果需要帮助，请提交 Github issue，或通过邮箱 zjiangaj@connect.ust.hk 联系江志锋。
