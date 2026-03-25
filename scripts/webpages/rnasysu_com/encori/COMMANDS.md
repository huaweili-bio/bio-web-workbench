# ENCORI 鍛戒护妯℃澘

鎵€鏈夊懡浠ら粯璁や娇鐢?PowerShell / Windows 璺緞銆?
## help

### `mirna_to_lncrna`

```powershell
python "scripts\webpages\rnasysu_com\encori\tasks\mirna_to_lncrna.py" --help
```

### `mrna_to_mirna`

```powershell
python "scripts\webpages\rnasysu_com\encori\tasks\mrna_to_mirna.py" --help
```

## smoke

### `mirna_to_lncrna`

```powershell
python "scripts\protocol_gate.py" --page-key rnasysu_com.encori --task-key mirna_to_lncrna --mirna-count 1 --execution-mode main_thread --current-boundary "杩欏洖鍚堝彧鍋?ENCORI smoke 楠岃瘉锛屼笉鍋氭壒閲忔寮忎换鍔★紝涓嶅仛璺ㄥ簱鍚庣画鍒嗘瀽銆? --job-dir "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_smoke_hsa_miR_21_5p" --output "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_smoke_hsa_miR_21_5p\protocol_check.json"
python "scripts\webpages\rnasysu_com\encori\tasks\mirna_to_lncrna.py" --mirna hsa-miR-21-5p --job-dir "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_smoke_hsa_miR_21_5p" --protocol-check-file "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_smoke_hsa_miR_21_5p\protocol_check.json"
```

### `mrna_to_mirna`

```powershell
python "scripts\protocol_gate.py" --page-key rnasysu_com.encori --task-key mrna_to_mirna --query-count 1 --execution-mode main_thread --current-boundary "杩欏洖鍚堝彧鍋?ENCORI mRNA -> miRNA smoke 楠岃瘉锛屼笉鍋氭壒閲忔寮忎换鍔★紝涓嶅仛璺ㄥ簱鍚庣画鍒嗘瀽銆? --job-dir "outputs\tasks\mRNA_miRNA_ENCORI_hg38_smoke_PIK3CA" --output "outputs\tasks\mRNA_miRNA_ENCORI_hg38_smoke_PIK3CA\protocol_check.json"
python "scripts\webpages\rnasysu_com\encori\tasks\mrna_to_mirna.py" --gene PIK3CA --job-dir "outputs\tasks\mRNA_miRNA_ENCORI_hg38_smoke_PIK3CA" --protocol-check-file "outputs\tasks\mRNA_miRNA_ENCORI_hg38_smoke_PIK3CA\protocol_check.json"
```

楠岃瘉瀹屾垚鍚庯紝濡傛灉璇ョ洰褰曞彧鐢ㄤ簬 smoke/test锛屽簲鍒犻櫎锛?
```powershell
Remove-Item -Recurse -Force "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_smoke_hsa_miR_21_5p"
Remove-Item -Recurse -Force "outputs\tasks\mRNA_miRNA_ENCORI_hg38_smoke_PIK3CA"
```

## task

### `mirna_to_lncrna`

```powershell
python "scripts\protocol_gate.py" --page-key rnasysu_com.encori --task-key mirna_to_lncrna --input-file "data\mirnas.txt" --execution-mode delegated_subagent --subagent-name EncoriWorker --current-boundary "杩欏洖鍚堝彧鍋?ENCORI 鍗曞簱鎵归噺鏌ヨ锛屼笉鍋氫氦闆嗭紝涓嶅仛楂樼壒寮傛€х瓫閫夈€? --job-dir "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_custom_batch" --output "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_custom_batch\protocol_check.json"
python "scripts\webpages\rnasysu_com\encori\tasks\mirna_to_lncrna.py" --input "data\mirnas.txt" --job-dir "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_custom_batch" --protocol-check-file "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_custom_batch\protocol_check.json"
```

### `mrna_to_mirna`

```powershell
python "scripts\protocol_gate.py" --page-key rnasysu_com.encori --task-key mrna_to_mirna --input-file "data\biomarker_genes.txt" --execution-mode delegated_subagent --subagent-name EncoriWorker --current-boundary "杩欏洖鍚堝彧鍋?ENCORI 鍗曞簱 mRNA -> miRNA 鎵归噺鏌ヨ锛屼笉鍋氫氦闆嗭紝涓嶅仛楂樼壒寮傛€х瓫閫夈€? --job-dir "outputs\tasks\mRNA_miRNA_ENCORI_hg38_custom_batch" --output "outputs\tasks\mRNA_miRNA_ENCORI_hg38_custom_batch\protocol_check.json"
python "scripts\webpages\rnasysu_com\encori\tasks\mrna_to_mirna.py" --input "data\biomarker_genes.txt" --job-dir "outputs\tasks\mRNA_miRNA_ENCORI_hg38_custom_batch" --protocol-check-file "outputs\tasks\mRNA_miRNA_ENCORI_hg38_custom_batch\protocol_check.json"
```

## debug

### `mirna_to_lncrna`

```powershell
python "scripts\webpages\rnasysu_com\encori\tasks\mirna_to_lncrna.py" --help
python "scripts\protocol_gate.py" --page-key rnasysu_com.encori --task-key mirna_to_lncrna --mirna-count 1 --execution-mode main_thread --current-boundary "杩欏洖鍚堝彧鍋?ENCORI 鍗曟潯 debug锛屼笉鍋氭壒閲忔寮忎换鍔°€? --job-dir "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_debug_single_query" --output "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_debug_single_query\protocol_check.json"
python "scripts\webpages\rnasysu_com\encori\tasks\mirna_to_lncrna.py" --mirna hsa-miR-21-5p --job-dir "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_debug_single_query" --raw-dir raw --protocol-check-file "outputs\tasks\miRNA_lncRNA_ENCORI_hg38_debug_single_query\protocol_check.json"
```

### `mrna_to_mirna`

```powershell
python "scripts\webpages\rnasysu_com\encori\tasks\mrna_to_mirna.py" --help
python "scripts\protocol_gate.py" --page-key rnasysu_com.encori --task-key mrna_to_mirna --query-count 1 --execution-mode main_thread --current-boundary "杩欏洖鍚堝彧鍋?ENCORI mRNA -> miRNA 鍗曟潯 debug锛屼笉鍋氭壒閲忔寮忎换鍔°€? --job-dir "outputs\tasks\mRNA_miRNA_ENCORI_hg38_debug_single_query" --output "outputs\tasks\mRNA_miRNA_ENCORI_hg38_debug_single_query\protocol_check.json"
python "scripts\webpages\rnasysu_com\encori\tasks\mrna_to_mirna.py" --gene PIK3CA --job-dir "outputs\tasks\mRNA_miRNA_ENCORI_hg38_debug_single_query" --raw-dir raw --protocol-check-file "outputs\tasks\mRNA_miRNA_ENCORI_hg38_debug_single_query\protocol_check.json"
```

## long-running

- 褰撳墠娌℃湁棰勭疆鐨勯暱鏃堕棿鍛戒护銆?- 澶ф壒閲忚緭鍏ユ枃浠舵煡璇㈠彲鑳借€楁椂杈冮暱锛岄粯璁や笉搴旂洿鎺ユ墽琛屻€?- 澶ф壒閲忚緭鍏ユ枃浠舵煡璇㈠繀椤讳氦缁欏瓙鏅鸿兘浣擄紝鑰屼笉鏄富绾跨▼鐩存帴鎵ц銆?- 姝ｅ紡浠诲姟涓€寰嬪厛杩愯 `scripts\protocol_gate.py`锛屾病鏈?`--protocol-check-file` 鏃惰剼鏈細鐩存帴澶辫触銆?- 缁欏瓙鏅鸿兘浣撲笅娲句换鍔℃椂锛屽繀椤诲厛璺?`help` 鎴?`smoke`锛岀‘璁よ矾寰勫拰鍙傛暟鍙敤銆?- 榛樿涓嶈鍦ㄥ懡浠や腑鏄惧紡鎸囧畾 `--timeout`锛涘彧鏈夌敤鎴锋槑纭姹傦紝鎴栨帓鏌ョ綉缁滈樆濉炴椂鎵嶅姞銆?- `help`/`smoke`/`test` 鍙敤浜庨獙璇侊紱楠岃瘉瀹屾垚鍚庯紝濡傛灉杈撳嚭鐩綍涓嶄綔涓烘寮忕粨鏋滀氦浠橈紝搴斿垹闄ゅ搴旀祴璇曠洰褰曘€?- 涓荤嚎绋嬩笅娲惧悗涓嶈鍚屾绛夊埌鍒板簳锛岄粯璁ゅ彧姹囨姤锛?  - 宸蹭笅娲?  - 瀛愭櫤鑳戒綋鍚?  - 鎵ц鍛戒护
  - 杈撳嚭璺緞
- 闇€瑕佺粨鏋滄椂锛屽啀鍗曠嫭鏌ヨ瀛愭櫤鑳戒綋鐘舵€佹垨杈撳嚭鏂囦欢銆?- 鐢ㄦ埛瑕佹眰鍋滄鏃讹紝搴旂珛鍗充腑鏂苟鍏抽棴瀵瑰簲瀛愭櫤鑳戒綋銆?
## 杈撳嚭绾﹀畾

- 褰撳墠鎺ㄨ崘杈撳嚭妯″紡鏄?`--job-dir`
- 涓€涓换鍔″彧鍒涘缓涓€涓洰褰曪紝鐩綍鍚嶅簲鑳界湅鍑衡€滅綉椤?+ 浠诲姟 + assembly/杈撳叆鏉ユ簮鈥?- 鐩綍鍐呭浐瀹氬寘鍚細
  - `encori_result.csv`
  - `summary.json`
  - 鍙€?`errors.json`
  - `temp/`
- `encori_result.csv` 涓細
  - `mirna_to_lncrna` 蹇呴』鍖呭惈 `query_lncrna_count`
  - `mrna_to_mirna` 蹇呴』鍖呭惈 `query_mirna_count`

## 输出约定

- 顶层只保留 `encori_result.csv`
- 其余调试与协议文件放入 `temp/`

