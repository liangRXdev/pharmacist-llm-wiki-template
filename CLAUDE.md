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

> [!important] `sources:` 一律填 **`raw/` 內的實際檔名**，不可填別的東西
> 這是 lint 內容過期檢查（`source_hash`）的唯一入口——填了非檔名的值，該頁就**永遠**不會被檢查，
> 且不會有任何警告（`check_stale` 對找不到 raw 檔者靜默跳過）。四種常見誤用與正解：
>
> | 誤用 | 正解 |
> |------|------|
> | `sources: [wiki/source-XXX]`（指向別的 wiki 頁） | 填**該 source 頁所引用的 raw 檔名**；頁面關係本來就靠正文的 `[[wiki/source-XXX]]` 雙鏈表達，不需要 frontmatter 再講一次 |
> | `sources: [多來源整合]`／`[多指引整合]` 等佔位字串 | 展開成正文所引用的每一個 raw 檔名（衍生頁常有 4–9 個，屬正常） |
> | `sources: [作者年份]` 這類短代號 | 填完整檔名 |
> | `sources: [憑印象寫的檔名]` | 以 `raw/` 內的**實際**檔名為準（見下方陷阱） |
>
> **唯一例外**：純線上來源（官方網站、線上資料庫）在 `raw/` 沒有對應檔，保留原字串即可，
> lint 會自動跳過，不影響任何指標。
>
> > [!warning] 三個實際踩過、且**都不會報錯**的陷阱
> > 1. **檔名含逗號**寫進 YAML flow list（`sources: [A, B.pdf]`）會被拆成多筆假來源 → **必須加引號**。
> > 2. **連字號不同碼位**：`-`（U+002D）vs `‐`（U+2010）肉眼相同，比對必失敗。核對時先 NFKC normalize。
> > 3. **`raw/` 內檔名本身被改壞**（例如失敗的 shell 指令產生的怪檔名）→ 來源看似消失。
> >    `ls raw/finish | grep '&&'` 可撈出這類殘骸。

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
4. 識別文中實體（藥物、疾病、機制）→ 更新或新建對應 entity/concept 頁；
   這些**衍生頁的 `sources:` 同樣填 raw 檔名**（繼承其所引用之 source 頁的檔名）並寫入 `source_hash`，
   否則它們會被排除在內容過期檢查之外（見 §二）
5. **回頭複核舊頁**：`grep` 既有頁面中與本主題相關的推論句，凡被新文獻推翻者就地改掉（見 §3.1.1）
6. 更新 `wiki/index.md`
7. 在 `wiki/log.md` 追加一筆 ingest 記錄
8. 回報：「已建立 N 頁，更新 M 頁，標記矛盾 K 處；lint 結果：通過 / 未通過 / 未執行，請確認」
   （三選一據實填寫；lint 沒跑就寫「未執行」，不得寫「通過」）

**一次 ingest 預期觸及 5–15 個 wiki 頁面。**

#### 3.1.1 Ingest 時的證據紀律（六條硬規則，常駐生效）

- **(a)** 引用效果量時，**連同「哪個分析模型」一起記**（主要分析 vs 敏感度分析、不同隨機效應模型）。
  裸數值無法對應到列/欄 → 表格已被抽取工具打散，切小檔重建，**不要照抄摘要**。
- **(b)** 原文自評的證據等級**一律重算**。與原文一致也要寫明一致；RoB 判定不同時**兩者並存並註明**，
  不要改掉自己的判定去迎合原文。
- **(c)** **不得**從「單一試驗為 null」推論「該次族群無效」（subgroup fallacy）。
  主張次族群差異需要**交互作用檢定**。
- **(d)** 新文獻推翻你先前寫下的推論時，**回頭改舊頁**，不要只新增一頁。
- **(e)** 誤植會沿連結擴散。發現時**沿反向連結全部更正**，並在 `log.md` 記錄更正處數。
- **(f)** 引用一律先過 **CrossRef DOI 存在性 gate**（`GET https://api.crossref.org/works/{DOI}`）再做語意比對。
  **existence 通過 ≠ claim 通過**；CrossRef 的更正登錄有系統性缺口，**另須 grep PDF 首頁**的
  `Corrected on` / `Erratum` / `Retracted`。查不到就說查不到，**不得猜測更正內容**。

> 每條規則的踩坑成因、CrossRef 回應的逐欄判讀、兩條硬規則的完整措辭：
> 見 [`docs/evidence-discipline.md`](docs/evidence-discipline.md)。

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

## Syntheses（跨文獻綜合）
- [[wiki/synthesis-主題]] — 綜合了哪幾篇、得出什麼

## Queries（查詢記錄）
- [[wiki/query-YYYY-MM-DD-主題]] — 問題摘要
```

> 六個分節須與 `Templates/index.md` 的骨架一致（`type` 定義見 §二）。

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

**首選工作流：pdfminer 抽全文正文 + Docling 逐表抽關鍵臨床表格。** MinerU 為次選/備援。

**先分流**：拿到 PDF 的第一件事是用 **pdf-inspector** 跑一次分類（<5 秒），依結果決定走法。
本表為 [`docs/pdf-extraction-strategy.md`](docs/pdf-extraction-strategy.md) **§0（唯一真相）的副本**——
要改分流走法，改那裡再同步這裡。

| 分流結果 | 走法 |
|---------|------|
| **無表格** | 不用碰 Docling，pdfminer 正文即收工 |
| **一般期刊論文**（≲30 頁、雙欄） | 正文 pdfminer；表格頁交 Docling |
| **大型指引**（≳50 頁，多為 Word 產生） | 正文＋標題階層 pdf-inspector；**只把關鍵閾值表**交 Docling |

> [!warning] 動手前必讀這三條
> 1. **Docling 不可直接餵整份大型 PDF（>~50 頁）**：CLI 多無 `--page-range`，記憶體會累積爆掉
>    （`std::bad_alloc`）並可能**拖垮整機**。務必先用 pypdf 切小檔（每檔 3–5 頁）再逐檔跑。
> 2. **Docling 遇跨頁寬表／橫向版面會重建錯，但 `exit 0` 不報錯**（失敗模式 A2）——
>    切小檔救不了，**不得硬套**，改走錨點交叉驗證。
> 3. **pdf-inspector 的表格輸出不可用於臨床數值表**：多欄表會塌陷，或把上標註腳編號黏到數值
>    **前面**（`≤2 ᵃ` → `a ≤2`），**數值全對、看起來完全正常**，但閾值判讀已經壞了。
>    **硬規則：任何要寫進頁面的臨床數值表，一律出自 Docling。**
>
> 三者的共通點：**都是安靜的失敗**——沒有 lint 會抓到，只有人會。

指令、選型判準（何時該切表給 Docling）、四工具的失敗備援邏輯與搶救法：
見 [`docs/pdf-extraction-strategy.md`](docs/pdf-extraction-strategy.md)。
安裝見 [`docs/setup-mineru.md`](docs/setup-mineru.md)。

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
