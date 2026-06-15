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
├── wiki/                 ← LLM 維護的知識頁面（LLM 可讀寫）
│   ├── index.md          ← 全庫目錄（每次 ingest 後更新）
│   └── log.md            ← 異動日誌（只追加，不刪改）
├── Templates/            ← 頁面 frontmatter 模板
└── CLAUDE.md             ← 本檔案（schema）
```

**規則：**
- `raw/` 內檔案：LLM **唯讀**，禁止修改
- `raw/finish/`：已 ingest 文獻；ingest 完成後由 LLM 移入
- `wiki/`：LLM 全權負責建立與更新
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
3. 在 `wiki/` 建立 source 頁面（摘要＋重點＋方法論評估）
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

1. 讀取所有 wiki 頁面（建議用連結圖譜腳本，見 §七）
2. 找出並回報：頁面間矛盾、被新文獻推翻的舊資訊、孤立頁面（無 inbound 連結）、只被提及卻無獨立頁面的重要概念、缺少交叉連結的頁面
3. 建議應補充的新文獻方向
4. 修正後在 `log.md` 寫入 lint 記錄

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

每篇**研究型**文獻的 `source` 頁面必須包含以下欄位，缺一不可（規範/指引型文件可酌情略過 PICO/效應量欄）：

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

若原始文獻資訊不足以填寫某欄位，標記 `[資訊不足]` 而非留空。

---

## 七、PDF 處理工具策略

### 7.1 Ingest 用途（建立 source 頁）

優先用 **MinerU** 將 PDF 轉 Markdown（表格重建品質最佳），再 Read 該 `.md` 分析。安裝與指令見 `docs/setup-mineru.md`。

原因：臨床論文關鍵數據多在表格；MinerU 的 HTML 表格輸出即使有殘餘錯誤，也比純文字易校正。常見殘餘問題：相鄰列合併、特殊符號誤判、CI 數值截斷 → 對照正文手動修正。

### 7.2 MinerU 失敗時的備援：pdfminer.six

MinerU 啟動失敗或 timeout 時，改用 pdfminer.six 提取純文字（快、跨平台）：

```bash
uv run --with pdfminer.six python -c "from pdfminer.high_level import extract_text; \
open('out.txt','w',encoding='utf-8').write(extract_text('<PDF路徑>'))"
```

> Windows 注意：`uvx --from pdfminer.six pdf2txt.py` 無效（`.py` 非 Win32 執行檔）；須用 `uv run --with pdfminer.six python -c` 呼叫 API。
> 備援工具產生的表格數值可信度較低 → 在 source 頁標記 `[需 MinerU 驗證]`，待 MinerU 正常後重跑確認。

### 7.3 快速查詢（非 ingest）

直接用 Read 工具讀 PDF（`pages` 參數分段）。若環境無 `pdftoppm` 致無法讀 PDF，先用 pdfminer 提取文字再 Read `.txt`。

---

## 八、會話開始時的標準動作

1. 讀取 `wiki/index.md`（掌握現有知識狀態）
2. 讀取 `wiki/log.md` 最後 10 筆（了解最近進展）
3. 向使用者確認：「目前 wiki 有 N 頁，最近一次操作是 [日期/動作]，今天要做什麼？」

---

## 九、安全與合規（分享前必讀）

- 本知識庫頁面多為**受著作權保護來源的摘要**，僅供**個人合理使用**；切勿將實際 wiki 內容公開散布（見 `DISCLAIMER.md`）。
- UpToDate、Micromedex、NCCN 等專有資料庫/指引內容**禁止重新散布**（含摘要改寫）。
- LLM 生成的劑量/交互作用內容可能含錯誤 → 臨床使用前**務必回核原始來源**。
- 公開 repo 前，確認已移除所有個人識別資訊與本機路徑。
