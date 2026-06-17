# CLAUDE.md — LLM 藥師知識庫操作規範（Schema）

> 本檔案是給 Claude Code（或任何 LLM Agent）閱讀的操作規範。
> 人類使用者不需手動編輯 `wiki/` 內的任何檔案；LLM 負責所有寫入。
> 這是一個**空白模板**：請依自己的環境替換 `<尖括號>` 內的佔位字串，再開始 ingest 文獻。

---

## 〇、使用前必做的替換

| 佔位字串 | 替換為 |
|----------|--------|
| `<VAULT_ROOT>` | 你的知識庫絕對路徑（如 `C:\Users\you\Documents\Vault`） |
| `<MINERU_PATH>` | MinerU 執行檔路徑（見 `docs/setup-mineru.md`），若不用可忽略 |
| `<TODAY>` | 每次對話開始時更新為今日日期 |

⚠️ 切勿在本檔或任何 wiki 頁面寫入 email、API key、個人帳號或病患資料。

---

## 一、目錄結構

```
Vault/
├── raw/                  ← 原始文獻（LLM 唯讀，不可修改）
│   ├── finish/           ← 已完成 ingest 的文獻（移入後仍唯讀）
│   └── assets/           ← 從文章下載的圖片
├── wiki/                 ← LLM 維護的知識頁面（LLM 可讀寫；.gitignore 白名單預設不追蹤內容）
│   ├── index.md          ← 全庫目錄（每次 ingest 後更新；首次由 Templates/index.md 複製）
│   └── log.md            ← 異動日誌（只追加，不刪改；首次由 Templates/log.md 複製）
├── Templates/            ← 頁面 frontmatter 模板 + index/log 空骨架
└── CLAUDE.md             ← 本檔案（schema）
```

**規則：**
- `raw/` 內檔案：LLM **唯讀**，禁止修改
- `raw/finish/`：已 ingest 文獻；ingest 完成後由 LLM 移入
- `wiki/`：LLM 全權負責建立與更新
- **首次使用**：若 `wiki/index.md` 或 `wiki/log.md` 不存在（fresh clone 只含 `wiki/.gitkeep`），先從 `Templates/` 複製對應骨架再開始
- `wiki/` 內容受 `.gitignore` 白名單保護（預設不追蹤），避免著作權摘要誤 commit 上 public repo
- 使用者只負責：放入原始文獻、提問、決定方向

---

## 二、Wiki 頁面格式規範

每個 wiki 頁面開頭須有 YAML frontmatter：

```yaml
---
title: 頁面標題
type: source | entity | concept | comparison | synthesis | query
tags: [標籤1, 標籤2]
sources: [原始檔案名1, 原始檔案名2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

**type 說明：**
| type | 用途 |
|------|------|
| `source` | 單一原始文獻的摘要頁 |
| `entity` | 藥物、疾病、機構、人名等實體頁 |
| `concept` | 概念/機制/理論頁 |
| `comparison` | 多項目比較表 |
| `synthesis` | 跨多文獻的綜合分析 |
| `query` | 使用者提問後產生的有價值答案頁 |

> **⚠️ entity 頁的定位（刻意設計，勿擴張）**：entity 頁是把文獻串接到藥物/疾病的**連結節點**，**不是** drug monograph。
> - **禁止**把藥物的劑量、交互作用、腎/肝功能調整、ADR、禁忌等**事實性內容抄寫進 wiki**——這些請即時查 **UpToDate / Micromedex**（權威且永遠最新）。
> - 原因有三：(1) 商業資料庫的內容**禁止再散布**（含摘要改寫，見 §九 / DISCLAIMER）；(2) 抄進來就會**過期**且需人工維護；(3) 不重造商業工具已做得更好的輪子。
> - entity 頁只放：本庫文獻對此藥物/疾病的**證據連結**（`[[wiki/source-…]]`）、跨文獻的觀察、本地（台灣健保/臨床）特殊註記。藥物事實一律導向外部工具。

**正文格式：**
- 頁面之間用 `[[wiki/頁面名稱]]` 建立雙向連結
- 引用原始文獻用 `> [!cite] 來源：[[raw/檔名]]`
- 矛盾處用 `> [!warning] 矛盾：...` 標記
- 數據/劑量/規範類內容須標明**來源年份與機構**

---

## 三、操作流程

### 3.1 Ingest（新增文獻）

使用者說：「請處理 raw/XXX.pdf（或貼上文字）」

1. 讀取原始文獻
2. 與使用者簡短討論重點（2–3 個核心發現）
3. 在 `wiki/` 建立 source 頁面（摘要＋重點＋方法論評估）；frontmatter 寫入 `source_hash`（raw 檔 sha256 前 16 碼，供 lint 內容過期檢查；多來源用 `{檔名: 雜湊}`）
4. 識別文中實體（藥物、疾病、機制）→ 更新或新建對應 entity/concept 頁
5. 更新 `wiki/index.md`
6. 在 `wiki/log.md` 追加一筆 ingest 記錄
7. 回報：「已建立 N 頁，更新 M 頁，請確認」

**一次 ingest 預期觸及 5–15 個 wiki 頁面。**

### 3.2 Query（提問查詢）

1. 讀取 `wiki/index.md` 找相關頁面
2. 精讀後合成答案
3. 答案附頁面引用（`[[wiki/XXX]]`）
4. 若答案有獨立保存價值 → 詢問是否存成 query 頁
5. 存檔則新建 `wiki/query-YYYY-MM-DD-主題.md`，更新 index，寫入 log

### 3.3 Lint（健康檢查）

採**兩階段**：先跑機械腳本（快、客觀），再由 LLM 做語意檢查。

**Phase 1：機械檢查（`tools/wiki_lint.py`）** — 從 vault 根目錄執行：

```bash
uv run --with pyyaml python tools/wiki_lint.py
```

- 輸出報告 `output/lint-YYYY-MM-DD.md` + stdout JSON 摘要；`--json` 只印不寫檔
- 涵蓋：壞鏈、孤立頁、單向連結、稀疏頁、frontmatter 缺欄、過期頁（raw 內容 sha256 ≠ 頁面 `source_hash`）、source 型別待確認、**PII 強制掃描**（身分證過檢核碼 / 手機 / email，命中即 🔴）
- source 頁 EBM 欄位依型別查核（見 §六 A/B 型）+ 圖譜指標（孤立率 <5%、壞鏈率 <2%、平均出鏈 ≥5、雙向率 ≥50%）
- 門檻常數在腳本頂部可調

> ⚠️ frontmatter 陷阱：`updated:`/`created:` 等日期欄位**不可**寫成 `2026-06-02 (註: ...)` — 括號內「冒號+空格」會破壞 YAML 解析。變更原因寫進 `log.md`，日期欄位保持純日期。

**Phase 2：LLM 語意檢查** — 腳本判不了的：頁面間矛盾（標 `> [!warning] 矛盾`）、被新文獻推翻的舊資訊、只被提及卻無獨立頁面的重要概念、應雙向卻單向的連結（參考 Phase 1 清單）。

**Phase 3：收尾** — 機械修正（補回鏈/frontmatter/壞鏈）→ 建議新文獻方向 → 在 `log.md` 寫入 lint 記錄。

---

## 四、index.md 維護規則

```markdown
## Sources（原始文獻摘要）
- [[wiki/source-論文標題]] — 一行摘要（YYYY，第一作者）

## Entities（實體）
- [[wiki/entity-藥物名]] — 藥物類別，主要適應症

## Concepts（概念）
- [[wiki/concept-主題]] — 一行描述

## Comparisons（比較）
- [[wiki/comparison-主題]] — 比較對象摘要

## Queries（查詢記錄）
- [[wiki/query-YYYY-MM-DD-主題]] — 問題摘要
```

---

## 五、log.md 格式規則（方便 grep 篩選）

合法動作（`動作` 欄）：`ingest`（建頁）、`query`（查詢存檔）、`lint`（健檢）、`tooling`（工具鏈/工程改動，如 lint 腳本、測試、CI）。

```
## [YYYY-MM-DD] ingest | 文獻標題
- 新建頁面：wiki/XXX.md, wiki/YYY.md
- 更新頁面：wiki/ZZZ.md（原因：...）

## [YYYY-MM-DD] query | 問題摘要
- 存檔：wiki/query-YYYY-MM-DD-主題.md

## [YYYY-MM-DD] lint | 健康檢查
- 修正矛盾：N 處
- 新增連結：M 處
- 孤立頁面處理：K 頁

## [YYYY-MM-DD] tooling | 工程改動摘要
- 變更：tools/wiki_lint.py、tests/、.github/workflows/ 等（非臨床內容）
```

---

## 六、領域特殊規則（臨床藥學）

- 藥物劑量、交互作用、禁忌：**必須標明來源**（Micromedex、UpToDate、仿單、官方指引）
- 給付資格：標明給付代碼與公告日期（依各國健保制度調整）
- 病患辨識欄位若出現在來源文件中：**自動遮罩**
  - 姓名：`王○明`（中間字遮罩）
  - 病歷號：`12****89`（頭尾保留 2 碼）
  - 身分證：`A12****90`
- Log 或 debug 輸出不得包含未遮罩的個人資料
- EBM 評等：摘要頁加入證據等級（RCT / Meta-analysis / Cohort / Expert Opinion）
- 多語藥物名稱：記錄本地語言、英文、通用名（INN）

### EBM source 頁面最低內容要求

**依來源型別套用不同欄位要求**（避免把單篇研究的 PICO/outcome 強套到 guideline）：

#### (A) 單篇研究型（RCT / cohort / case-control / meta-analysis / 觀察性資料庫分析）
必須包含以下 8 欄，缺一不可：

| 欄位 | 內容要求 |
|------|---------|
| **Study design** | RCT / cohort / case-control / meta-analysis 等 |
| **PICO** | P / I / C / O 各自明確描述，不可合併 |
| **Primary outcome** | 指標名稱 + effect size + 95% CI + p value 或 NNT |
| **Secondary outcomes** | 同上格式（若有） |
| **RoB tool** | RoB 2.0 / ROBINS-I / NOS / QUADAS-2 + 整體判斷 |
| **GRADE** | High / Moderate / Low / Very Low + 主要降級原因 |
| **Applicability** | 對本地臨床實務的適用性說明 |
| **Bottom line** | 單句結論，直接可用於臨床決策 |

#### (B) Guideline / 共識 / 藥物基因指引 / 工具量表 / 法規清單 / 衛教
**不適用** PICO / Primary / Secondary outcome / RoB（單篇研究概念）。最低必備 3 欄：

| 欄位 | 內容要求 |
|------|---------|
| **Study design** | 此處填「來源型別」：guideline / consensus / criteria / regulatory list / education 等 + 發布機構年份 |
| **Applicability** | 對本地臨床實務的適用性 |
| **Bottom line** | 單句可用於臨床決策的結論 |

> guideline 類若採自有證據分級（COR-LOE、KDIGO 1A/2B、CPIC strength），記於 GRADE 欄或正文即可，不強制 RoB。

#### 共通規則
- 欄名中英皆可（`Study design`／研究設計、`Applicability`／適用性、`Bottom line`／單句結論）；`tools/wiki_lint.py` 已支援別名比對。
- 資訊不足以填寫某欄位時標記 `[資訊不足]` 而非留空。
- 型別判定：lint 腳本以 Study design 欄關鍵字自動分流（研究關鍵字→A 型查 8 欄；其餘→B 型查 3 欄）。

---

## 七、PDF 處理工具策略

### 7.1 Ingest 用途（建立 source 頁）

**首選工作流：分工＝pdfminer 全文正文 + Docling 逐表（關鍵表格）。** MinerU 退為「需整檔一次出、可接受黏字」的次選。

**(A) 正文：pdfminer.six** — 敘述/建議分級等文字段落，抽全文後 Read `.txt`（快、跨平台、穩定）：

```bash
uv run --with pdfminer.six python -c "from pdfminer.high_level import extract_text; \
open('out.txt','w',encoding='utf-8').write(extract_text('<PDF路徑>'))"
```
> Windows 注意：`uvx --from pdfminer.six pdf2txt.py` 無效（`.py` 非 Win32 執行檔）；須用 `uv run --with pdfminer.six python -c` 呼叫 API。

**(B) 關鍵臨床表格：Docling（切小檔逐表）★ 表格品質最佳**
- **優點**：原生輸出 GFM markdown 表（可直接貼入 wiki）、欄列分明、字元與臨床閾值準確（實測勝 MinerU 的黏字、字母混淆、閾值污染）。
- **適合時機**：劑量表、不良反應表、診斷閾值表、治療決策矩陣等高精度臨床表。
- **限制**：CLI 多無 `--page-range`；整份大型 PDF（>~50 頁）會累積記憶體爆掉（`std::bad_alloc`）並可能拖垮整機 → **務必先用 pypdf 切小檔（每檔 3–5 頁，只含目標表格頁）再逐檔跑**；輸出表後常嵌 base64 圖片字串，以 `grep -v "data:image"` 剝除；模型載入較慢。

```bash
# Step 1：pypdf 切目標表格頁（0-based index）
uv run --with pypdf python -c "from pypdf import PdfReader,PdfWriter; r=PdfReader('<PDF>'); w=PdfWriter(); [w.add_page(r.pages[i]) for i in range(<起>,<迄>+1)]; w.write(open('split.pdf','wb'))"
# Step 2：對小檔跑 Docling
docling split.pdf --to md --output <輸出目錄> --table-mode accurate
```

**(C) MinerU：整檔一次轉換（次選/備援）** — 安裝與指令見 `docs/setup-mineru.md`。其 `_content_list.json` 可快速定位每張表的頁碼（即使整份表格品質不佳，用於決定 Docling 要切哪幾頁）。HTML 表格殘餘問題：相鄰列合併、黏字、字母混淆（II↔Il）、CI 截斷 → 對照正文修正。

### 7.2 失敗時的備援邏輯

- **Docling `bad_alloc`**（整份崩潰）→ 確認背景進程已死 → 改切更小檔逐表 → 仍失敗則該表退 MinerU 或 pdfminer + 對照原文手動建表。
- **MinerU 啟動失敗/殭屍進程** → 清殭屍 python 進程後重試，或改用 Docling（切小檔）抽表。
- **兩者皆失敗** → pdfminer 抽全文正文；表格數值標記 `[需 Docling/MinerU 驗證]`，待工具正常後重跑該表確認。

### 7.3 快速查詢（非 ingest）

直接用 Read 工具讀 PDF（`pages` 參數分段）。若環境無 `pdftoppm` 致無法讀 PDF，先用 pdfminer 提取文字再 Read `.txt`。

---

## 八、會話開始時的標準動作

0. 確認 `wiki/index.md`、`wiki/log.md` 存在；若缺（fresh clone）→ 從 `Templates/` 複製對應骨架後再繼續
1. 讀取 `wiki/index.md`（掌握現有知識狀態）
2. 讀取 `wiki/log.md` 最後 10 筆（了解最近進展）
3. 向使用者確認：「目前 wiki 有 N 頁，最近一次操作是 [日期/動作]，今天要做什麼？」

---

## 九、安全與合規（分享前必讀）

- 本知識庫頁面多為**受著作權保護來源的摘要**，僅供**個人合理使用**；切勿將實際 wiki 內容公開散布（見 `DISCLAIMER.md`）。
- UpToDate、Micromedex、NCCN 等專有資料庫/指引內容**禁止重新散布**（含摘要改寫）。
- LLM 生成的劑量/交互作用內容可能含錯誤 → 臨床使用前**務必回核原始來源**。
- 公開 repo 前，確認已移除所有個人識別資訊與本機路徑。
