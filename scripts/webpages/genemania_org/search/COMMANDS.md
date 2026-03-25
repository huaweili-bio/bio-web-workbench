# GeneMANIA 鍛戒护妯℃澘

鎵€鏈夊懡浠ら粯璁や娇鐢?PowerShell / Windows 璺緞銆?
## help

`help` 浠呯敤浜庢煡鐪嬪弬鏁帮紝涓嶉渶瑕佸崗璁椄闂ㄦ枃浠躲€?
```powershell
python "scripts\webpages\genemania_org\search\tasks\gene_set_to_report_figure.py" --help
```

## smoke

```powershell
python "scripts\protocol_gate.py" --page-key genemania_org.search --task-key gene_set_to_report_figure --query-count 1 --execution-mode main_thread --current-boundary "杩欏洖鍚堝彧鍋?GeneMANIA 鍗曠粍鍩哄洜闆?smoke 楠岃瘉锛屼笉鍋氭壒閲忎换鍔★紝涓嶅仛鐩綍澶栧垎鏋愩€? --job-dir "outputs\tasks\GeneSetAnalysis_GeneMANIA__smoke_GABBR1_PIK3CA_ITGB2" --output "outputs\tasks\GeneSetAnalysis_GeneMANIA__smoke_GABBR1_PIK3CA_ITGB2\protocol_check.json"
python "scripts\webpages\genemania_org\search\tasks\gene_set_to_report_figure.py" --gene GABBR1 --gene PIK3CA --gene ITGB2 --job-dir "outputs\tasks\GeneSetAnalysis_GeneMANIA__smoke_GABBR1_PIK3CA_ITGB2" --protocol-check-file "outputs\tasks\GeneSetAnalysis_GeneMANIA__smoke_GABBR1_PIK3CA_ITGB2\protocol_check.json"
```

楠岃瘉瀹屾垚鍚庯紝濡傛灉璇ョ洰褰曞彧鐢ㄤ簬 smoke/test锛屽簲鍒犻櫎锛?
```powershell
Remove-Item -Recurse -Force "outputs\tasks\GeneSetAnalysis_GeneMANIA__smoke_GABBR1_PIK3CA_ITGB2"
```

## task

```powershell
python "scripts\protocol_gate.py" --page-key genemania_org.search --task-key gene_set_to_report_figure --query-count 1 --execution-mode main_thread --current-boundary "杩欏洖鍚堝彧鍋?GeneMANIA 鍗曠粍鍩哄洜闆嗙綉椤靛鍑猴紝杈撳嚭娓呯悊鍚庣殑绗竴椤?PDF 鍜屽尮閰?PNG锛屼笉鍋氭壒閲忎换鍔★紝涓嶈縼 Java/R 娴佺▼銆? --job-dir "outputs\tasks\GeneSetAnalysis_GeneMANIA__custom" --output "outputs\tasks\GeneSetAnalysis_GeneMANIA__custom\protocol_check.json"
python "scripts\webpages\genemania_org\search\tasks\gene_set_to_report_figure.py" --gene GABBR1 --gene PIK3CA --gene ITGB2 --job-dir "outputs\tasks\GeneSetAnalysis_GeneMANIA__custom" --protocol-check-file "outputs\tasks\GeneSetAnalysis_GeneMANIA__custom\protocol_check.json"
```

濡傜己灏?PNG 娓叉煋渚濊禆锛屽彲鍏堝畨瑁咃細

```powershell
python -m pip install pypdfium2
```

## debug

```powershell
python "scripts\webpages\genemania_org\search\tasks\gene_set_to_report_figure.py" --help
python "scripts\protocol_gate.py" --page-key genemania_org.search --task-key gene_set_to_report_figure --query-count 1 --execution-mode main_thread --current-boundary "杩欏洖鍚堝彧鍋?GeneMANIA 鍗曠粍鍩哄洜闆?debug锛屼笉鍋氭壒閲忎换鍔°€? --job-dir "outputs\tasks\GeneSetAnalysis_GeneMANIA__debug_single_query" --output "outputs\tasks\GeneSetAnalysis_GeneMANIA__debug_single_query\protocol_check.json"
python "scripts\webpages\genemania_org\search\tasks\gene_set_to_report_figure.py" --gene GABBR1 --gene PIK3CA --gene ITGB2 --job-dir "outputs\tasks\GeneSetAnalysis_GeneMANIA__debug_single_query" --protocol-check-file "outputs\tasks\GeneSetAnalysis_GeneMANIA__debug_single_query\protocol_check.json"
```

## long-running

- 褰撳墠娌℃湁棰勭疆鐨勬壒閲忔枃浠跺鍑哄懡浠?- 褰撳墠浠诲姟鍙敮鎸佸崟涓熀鍥犻泦
- 姝ｅ紡浠诲姟涓€寰嬪厛杩愯 `scripts\protocol_gate.py`锛涙病鏈?`--protocol-check-file` 鏃惰剼鏈細鐩存帴澶辫触
- `help`/`smoke`/`test` 鍙敤浜庨獙璇侊紱楠岃瘉瀹屾垚鍚庯紝濡傛灉杈撳嚭鐩綍涓嶄綔涓烘寮忕粨鏋滀氦浠橈紝搴斿垹闄ゅ搴旀祴璇曠洰褰?- 鍚庣画鑻ユ柊澧炴壒閲?TSV/CSV 浠诲姟锛屽繀椤诲崟鐙柊澧?batch task锛屽苟鎸変粨搴撳崗璁鎵归噺杈撳叆璧板娲捐鍒?
## 杈撳嚭绾﹀畾

- 褰撳墠鎺ㄨ崘杈撳嚭妯″紡鏄?`--job-dir`
- 涓€涓换鍔″彧鍒涘缓涓€涓洰褰曪紝鐩綍鍐呭浐瀹氬寘鍚細
  - `genemania_report.pdf`
  - `genemania_report.png`
  - `summary.json`
  - 鍙€?`errors.json`
  - `temp/`
- `genemania_report.png` 涓?`genemania_report.pdf` 鍐呭搴斾繚鎸佷竴鑷达紝閮芥槸鈥滆鍒囧悗鐨勭涓€椤垫垚鍝佲€?
