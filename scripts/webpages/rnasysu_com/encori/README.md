# ENCORI 网页说明

网页地址：`https://rnasysu.com/encori/`

## 网页作用

该网页用于查询 RNA-RNA 互作信息。当前目录只封装 ENCORI 单库任务，不调用其他数据库。

## 当前已代码化任务

- `mirna_to_lncrna`
  - 输入：一个或多个 miRNA，支持命令行参数、文本文件输入、CSV 输入
- 输出：单任务目录中的 `encori_result.csv`、`summary.json`、可选 `errors.json`，以及 `temp/` 中间目录
  - 能力：查询 `miRNA -> lncRNA` 互作结果，保留 ENCORI 原始位点级列，并补 `query_mirna`、`query_lncrna_count`
  - 批量输入执行策略：如果输入是批量 CSV/TXT 文件，默认必须交给子智能体执行
  - 正式执行要求：必须先用 `scripts\protocol_gate.py` 生成协议闸门文件，再通过 `--protocol-check-file` 运行任务脚本
  - 命令约定：默认不要显式指定 `--timeout`，除非用户明确要求或调试网络问题
  - 总文件生成方式：直接生成的总文件，不是子文件拼接

- `mrna_to_mirna`
  - 输入：一个或多个 gene symbol，支持命令行参数、文本文件输入、CSV 输入
- 输出：单任务目录中的 `encori_result.csv`、`summary.json`、可选 `errors.json`，以及 `temp/` 中间目录
  - 能力：查询 `mRNA biomarker -> miRNA` 互作结果，保留 ENCORI 原始导出列，并补 `query_gene_symbol`、`query_mirna_count`
  - 默认过滤：`assembly=hg38`、`clipExpNum>=1`、`degraExpNum>=0`、`pancancerNum>=0`、`programNum>=1`、`program=None`
  - 批量输入执行策略：如果输入是批量 CSV/TXT 文件，默认必须交给子智能体执行
  - 正式执行要求：必须先用 `scripts\protocol_gate.py` 生成协议闸门文件，再通过 `--protocol-check-file` 运行任务脚本
  - 命令约定：默认不要显式指定 `--timeout`，除非用户明确要求或调试网络问题
  - 总文件生成方式：直接生成的总文件，不是子文件拼接

## 当前目录边界

- 当前目录只实现 ENCORI 单库网页任务
- 不调用 LncBase
- 不调用 miRDB
- 不做交集
- 不做高特异性筛选
- 不新增 `pair`、`consensus`、`intersection` 等跨库任务到本目录

## 当前目录约定

- `common/`：只供本网页使用的 HTTP、TSV/HTML 与输出辅助逻辑
- `tasks/`：本网页可直接运行的任务脚本
- `manifest.py`：本网页的机器可读说明
- `COMMANDS.md`：给人工或智能体直接复用的命令模板

## 输出目录约定

- 每次任务只创建一个清晰命名的任务目录
- 任务目录内只保留：
- `encori_result.csv`
  - `summary.json`
  - 可选 `errors.json`
  - `temp/`
- `temp/` 用于保存：
  - 原始输入文件副本
  - 归一化后的输入列表
  - 原始 API/下载响应
  - 其他执行该任务需要的中间文件
- smoke/test 目录只用于验证；验证完成后应删除，不应长期保留在 `outputs/tasks/` 中

## 结果反馈约定

- 汇报结果时，优先说明：
  - 使用了哪个脚本
  - 输入文件是什么
  - 总文件是“直接生成”还是“子文件拼接”
  - 结果目录路径
  - 总文件路径
  - 是否生成 `errors.json`
  - 命中的查询数量与总记录数
- 如果是长任务下派后的反馈，主线程默认不等待到底；需要结果时再单独查询
- 如果本次只做 smoke/test 验证，反馈后应清理该测试目录，不把它当成正式结果目录保留

## 已知限制

- 当前实现依赖 ENCORI 官方公开下载接口
- 当前只封装了 `miRNA -> lncRNA` 与 `mRNA biomarker -> miRNA`
- 默认不执行长时间批量任务；先做 `help` 或 smoke 验证
- 批量文件输入默认由子智能体执行，主线程只负责下派和回报路径
- 对 `mrna_to_mirna` 而言，`No Available results.` 按零结果成功处理；参数错误或网络错误才写入 `errors.json`
- 没有 `--protocol-check-file` 的正式任务将被脚本直接拒绝

## 后续可扩展方向

- 在同一网页目录下新增更细粒度的筛选与辅助任务
- 补充更多 ENCORI 单库查询方向
- 在别的独立任务目录中再处理跨库交集与候选筛选
