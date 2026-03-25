# GeneMANIA 网页说明

网页地址：`https://genemania.org/`

## 网页作用

该网页用于根据输入基因集构建关联网络，并可导出网页报告。当前目录只封装 `GeneMANIA` 的“单个基因集 -> 清理后 PDF/PNG 成品图”任务。

## 当前已代码化任务

- `gene_set_to_report_figure`
  - 输入：单个基因集，使用重复 `--gene` 参数传入；支持逗号分隔，并按输入顺序去重
- 输出：单任务目录中的 `genemania_report.pdf`、`genemania_report.png`、`summary.json`、可选 `errors.json`，以及 `temp/`
  - 能力：打开 GeneMANIA 搜索结果页，应用 `circle` 布局和 `Top 5 functions` 着色，调用网页内置 `report()` 下载报告，再只保留第一页并裁掉页眉/页脚区域
  - PNG 规则：正式 PNG 是“清理后第一页 PDF 的位图渲染”，不是网页全页截图，也不是纯 network PNG
  - 正式执行要求：必须先用 `scripts\protocol_gate.py` 生成协议闸门文件，再通过 `--protocol-check-file` 运行任务脚本
- 依赖说明：生成 `genemania_report.png` 需要额外安装 `pypdfium2`；缺失时脚本会明确报错，不输出半成品

## 当前目录边界

- 当前目录只实现 GeneMANIA 单组基因集的网页导出
- 不迁入 Java CLI 批跑工作流
- 不迁入 `genemania_report.R`
- 不实现 TSV/CSV 多 query 批处理
- 不输出网页工具栏截图、原始网络 PNG 或原始多页报告作为正式交付

## 当前目录约定

- `common/`：只放本网页需要的轻量输出辅助逻辑
- `tasks/`：本网页可直接运行的任务脚本
- `manifest.py`：本网页机器可读说明
- `COMMANDS.md`：人工或智能体直接复用的命令模板

## 输出目录约定

- 每次任务只创建一个清晰命名的任务目录
- 任务目录内正式保留：
- `genemania_report.pdf`
- `genemania_report.png`
  - `summary.json`
  - 可选 `errors.json`
  - `temp/`
- `temp/` 用于保存：
  - 归一化后的输入基因列表
  - 调试时保留的原始下载 PDF 或其他中间文件
- smoke/test 输出只用于验证；验证完成后应删除

## 结果反馈约定

- 汇报结果时，优先说明：
  - 使用了哪个脚本
  - 查询基因列表
  - 结果目录路径
- `genemania_report.pdf` 路径
- `genemania_report.png` 路径
  - 是否生成 `errors.json`
  - 最终 URL
  - 实际选中的 function 数量

## 已知限制

- 当前实现依赖 GeneMANIA 网页前端对象 `Query.current.result`
- 当前 PNG 渲染依赖 `pypdfium2`
- 当前不支持批量文件输入；如需批量，应单独新增 batch task

## 后续可扩展方向

- 在同一网页目录下新增批量基因集导出任务
- 增加网络类型、相关基因数量等网页侧可控参数
- 增加失败时的网页诊断截图输出
