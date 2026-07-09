# CLAUDE.md — LLM 藥師知識庫操作規範（Schema）

> 本檔案是給 Claude Code（或任何 LLM Agent）閱讀的操作規範。
> 人類使用者不需手動編輯 `wiki/` 內的任何檔案；LLM 負責所有寫入。

---

## 〇、使用前須知

**本檔開箱即用，不需要做任何全域字串取代。** 所有路徑都是相對於知識庫根目錄的相對路徑，
只要你在該目錄下啟動 Claude Code 就會正確解析。

§七 的指令範例裡有 `<PDF>`、`<起>`、`<迄>`、`<輸出目錄>` 等尖括號——那些是**執行當下由 LLM
代入的參數**，不是要你事先手動填寫的佔位字串。

依環境需要調整的只有一處，且為選用：**§六 領域特殊規則**——你不在台灣、或不需要健保給付與
多語藥物標籤規則時，改寫該節即可。

（MinerU 的執行檔路徑不在本檔，設定方式見 `docs/setup-mineru.md`。）

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
5. **回頭複核舊頁**：`grep` 既有頁面中與本主題相關的推論句，凡被新文獻推翻者就地改掉（見 §3.1.1）
6. 更新 `wiki/index.md`
7. 在 `wiki/log.md` 追加一筆 ingest 記錄
8. 回報：「已建立 N 頁，更新 M 頁，標記矛盾 K 處；lint 結果：通過 / 未通過 / 未執行，請確認」
   （三選一據實填寫；lint 沒跑就寫「未執行」，不得寫「通過」）

**一次 ingest 預期觸及 5–15 個 wiki 頁面。**

#### 3.1.1 Ingest 時的證據紀律（實戰累積，逐條都有踩坑成因）

**(a) 引用的效果量必須連同「哪個分析模型」一起記。**
同一篇論文對同一 outcome 常給出多個估計（貝氏主要分析 vs frequentist 敏感度分析；不同隨機效應模型）。
點估計可能相近而信賴區間、異質性（I²）差異極大，**指引引用的未必是原文的主要分析**。
頁面上逐列標明模型；`grep` 到一串裸數值卻無法判斷哪個屬於哪一列時，**代表表格結構已被抽取工具打散**
→ 依 §7.1 切小檔重建表格，不要照抄摘要。

**(b) 原文自評的證據等級一律重算，但重算不等於一定會推翻。**
重算與原文一致時，**照樣寫入重算過程並註明一致**——那本身是可信度訊號。
不一致時才標 `> [!warning] 矛盾`。RoB 判定與原作者不同屬正常（判斷尺度差異，非事實爭議）
→ **兩者並存並註明**，不要單方面改掉自己的判定去迎合原文。

**(c) 不要從「單一試驗為 null」推論「該次族群無效」。**
這是 subgroup fallacy，而且極易寫進 concept 頁變成假的臨床建議。
要主張次族群差異，需要**交互作用檢定**，不是「A 試驗顯著、B 試驗不顯著」。
單一試驗的 null 多半是**精確度不足**，不是**特異性無效**。

**(d) 新文獻可能推翻你自己先前寫下的推論——回頭改，不要只是新增一頁。**
知識庫的價值在於一致性。新增頁而不修舊頁，等於讓被推翻的結論繼續以「已寫下」的權威留在庫裡。
ingest 完成前，把本次主題相關的舊頁推論句逐一複核。

**(e) 誤植會沿著連結擴散。**
把 pooled 值標成某單一試驗的結果、把敏感度分析標成主要分析——這類錯誤一旦寫進 source 頁，
後續每一頁都會照抄。發現時**沿著反向連結全部更正**，並在 log.md 記錄更正處數。

**(f) DOI 存在性查核（anti-hallucination gate），以及它抓不到的東西。**

建立 source 頁與查核引用時，先做**確定性**的存在性檢查，再做語意比對：

```
GET https://api.crossref.org/works/{DOI}      # 免金鑰
```
- 404 / 無 `message` → ❌ DOI 不存在（捏造或錯字），**不進入語意比對**
- 有回應 → 比對回傳 `title` 與所引標題是否為同一篇（token overlap，不求字面全等）
- 檢查 `update-to` / `updated-by` → 撤稿 / 更正 / 表達關切

> [!warning] 硬規則 1：existence 通過 ≠ claim 通過
> 機器抓得到「不存在」與「DOI 對到別篇」，**抓不到「誤引述」**。
> 存在性通過只解鎖語意比對，不能取代它。CrossRef 若無法連線，於該列標
> 「existence gate skipped」並照常做語意比對——**降級為明示的不確定，不可降級為靜默通過**。

> [!warning] 硬規則 2：CrossRef 的更正登錄有系統性缺口，必須另查 PDF 首頁
> 實測遇過同一期刊連續兩篇論文，PDF 首頁明載 `Corrected on <日期>`，
> 而 CrossRef 的 `update-to` / `updated-by` **皆為空**。連續命中即非個案。
>
> 因此每篇都做兩件事：
> 1. 查 CrossRef `update-to` / `updated-by`
> 2. **`grep` 抽出的 `_extracted.txt` 前 ~100 行是否有 `Corrected on` / `Erratum` / `Retracted`**
>
> 任一命中即在頁面標記。CrossRef 空而 PDF 有 → 標「CrossRef 未反映該更正，內容待原站確認」，
> **不得猜測更正內容**（§六「查不到就說查不到」）。

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

#### (B) Guideline / 共識 / 藥物基因指引 / 工具量表 / 法規清單 / 衛教 / **narrative review**
**不適用** PICO / Primary / Secondary outcome / RoB（單篇研究概念）。最低必備 3 欄：

| 欄位 | 內容要求 |
|------|---------|
| **Study design** | 此處填「來源型別」：guideline / consensus / criteria / regulatory list / education 等 + 發布機構年份 |
| **Applicability** | 對本地臨床實務的適用性 |
| **Bottom line** | 單句可用於臨床決策的結論 |

> guideline 類若採自有證據分級（COR-LOE、KDIGO 1A/2B、CPIC strength），記於 GRADE 欄或正文即可，不強制 RoB。
> narrative review 可另加 `## SANRA 評估`（非 lint 強制）：是否說明立論理由、是否描述文獻檢索、
> 關鍵論述是否有引用、是否承認相反證據。**未描述檢索策略者不可作為證據強度之依據。**

#### 共通規則
- 欄名中英皆可（`Study design`／研究設計、`Applicability`／適用性、`Bottom line`／單句結論）；`tools/wiki_lint.py` 已支援別名比對。
- 資訊不足以填寫某欄位時標記 `[資訊不足]` 而非留空。

#### 型別判定與 Study design 欄的寫法（**踩過坑，務必照做**）

lint 以 Study design 欄的關鍵字自動分流：研究關鍵字 → A 型查 8 欄；非研究線索 → B 型查 3 欄；
**兩者皆無或語義衝突 → `undetermined`，不靜默降級，以 8 欄檢視並交人判定。**

**三種可被辨識的寫法**（任一即可；標題可帶編號或附註，欄名支援中文別名）：

```markdown
**Study design**：多中心雙盲 RCT          ← 同一行帶冒號
| Study design | 多中心雙盲 RCT |          ← 表格列（`| 文件性質 | … |` 等別名亦可）
## Study design                            ← 標題 + 下一行內容
### 1. Study Design                        ← 帶編號亦可
## Study Design / 文件性質                 ← 帶附註亦可

- **類型**：多中心、雙盲、1:1 隨機分派 RCT
```

> **標題優先於行內比對**：RoB 表常以 `| 研究設計 | 🟡 Some |` 作為 domain 列名，行內比對會抓到
> 偏誤評等而非研究設計。頁面若有 Study design 標題，該標題才是權威。

> [!warning] Study design 欄裡**不要寫否定句，也不要寫他篇論文的設計**
> 分流是**子字串比對，不懂否定，也不懂引用語境**。以下寫法會讓一篇綜論被誤判為單篇研究，
> 進而逼你去補**根本不存在**的 primary/secondary outcome：
>
> - ❌ `Seminar（系統性敘述回顧）；……；無 meta-analysis` ← 否定句裡的關鍵字被抓走
> - ❌ `Narrative review（非 systematic review / meta-analysis）` ← 同上
> - ❌ `敘述回顧；以 <某作者> <年份> 之 meta-analysis 為主要引用依據` ← 抓到的是**他篇**的設計
>
> 腳本端已有三道防護：(1) narrative review 類關鍵字納入非研究線索；
> (2) 兩類關鍵字同時出現時採**位置規則**——先出現者宣告型別（設計宣告在前，引用/否定在後）；
> (3) 標題只是後備線索——Study design 欄已明確宣告研究設計時，標題裡的非研究字樣（如「量表 /
> scale」）不得否決它。
> 但**治本做法是寫乾淨**：
>
> - ✅ `**來源型別**：受邀綜論（invited narrative review），期刊年份`
> - 否定句、他篇引用一律移到 `## SANRA 評估` 或正文，**不要放進 Study design 欄**。

> [!important] 收工前必查分流計數（兩個方向都要看）
> `--json` 摘要中的 `source_study` / `source_guideline` / `source_undetermined` 是分流是否正確的唯一可見訊號：
>
> - 單篇研究被算進 `source_guideline` → Study design 欄沒被辨識到，**8 欄檢查靜默失效**
> - 綜論 / guideline 被算進 `source_study` → 過度觸發，會逼你補不存在的 outcome 欄位
> - `source_undetermined` 增加 → Study design 欄缺失或關鍵字衝突；**腳本刻意不選邊，等你判定**
>
> **`ebm_missing_study` 非 0 時，先確認那頁真的是單篇研究，再決定要不要補。**
> 對 narrative review 硬編 primary/secondary outcome 違反本節 (B)，且等於憑空捏造資料。

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
- **適合時機**：劑量表、不良反應表、診斷閾值表、治療決策矩陣、**多模型敏感度分析表**等高精度表。
- **限制**：CLI 多無 `--page-range`；整份大型 PDF（>~50 頁）會累積記憶體爆掉（`std::bad_alloc`）並可能拖垮整機 → **務必先用 pypdf 切小檔（每檔 3–5 頁，只含目標表格頁）再逐檔跑**；輸出表後常嵌 base64 圖片字串，以 `grep -v "data:image"` 剝除；模型載入較慢。

> [!important] **何時必須切表給 Docling**（判斷徵兆，不是憑感覺）
> 當 pdfminer 抽出的數字**逐一正確、但欄列對應被打散**時。典型症狀：`grep` 到一串裸數值
> （`0.86 (0.72 to 0.98)`、`0.91 (0.85 to 0.97)`…）卻**無法判斷哪個屬於哪一列/哪一欄**。
>
> 此時若「照抄摘要的那個數字」，就會把**敏感度分析誤當成主要分析**——而指引引用的
> 往往正是敏感度分析那一列。這種錯誤不會被任何 lint 抓到。

```bash
# Step 0：先定位表格在第幾頁（不必先跑 MinerU）
uv run --with pypdf python -c "from pypdf import PdfReader; r=PdfReader('<PDF>'); [print('page_idx',i) for i,p in enumerate(r.pages) if '<表中獨特字串>' in (p.extract_text() or '')]"
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
