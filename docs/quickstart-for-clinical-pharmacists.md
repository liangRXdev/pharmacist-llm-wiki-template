# 新手 Quick Start（給臨床藥師）

> 這份文件假設你**不寫程式**。只回答四個問題：安裝什麼、文獻怎麼放、怎麼跟 Claude Code 說話、
> 怎麼確認沒出錯也沒洩漏資料。
>
> 主 README 的〈快速開始〉是給工程使用者的濃縮版；兩者步驟相同，這裡把每一步拆開解釋。
>
> 動手前請先讀 [`DISCLAIMER.md`](../DISCLAIMER.md)。**LLM 摘要會出錯**，尤其是劑量與給付規定；
> 這個工具是你的讀書筆記，不是臨床決策依據。

---

## 1. 我要安裝什麼？

三樣東西，前兩樣是必要的。

### （1）Claude Code — 實際幹活的 LLM agent

依官方指示安裝：<https://claude.com/claude-code>。安裝後在**終端機**（Windows 用 PowerShell，
macOS 用 Terminal）裡輸入 `claude` 就能啟動。

### （2）uv — 用來執行本 repo 的 Python 腳本

你不需要懂 Python，也**不需要事先安裝 Python**。`uv` 會在需要時自動處理。

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows（PowerShell）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

裝好後關掉終端機再重開，輸入 `uv --version` 有版本號就成功了。

### （3）Obsidian — 選用，但強烈建議

<https://obsidian.md>。它讓你用滑鼠瀏覽 wiki 頁面之間的雙向連結，還有 Graph View 可以看知識圖譜
長成什麼樣。**不裝也能用**——`wiki/` 裡就是一般的 Markdown 檔，任何編輯器都打得開。

> **PDF 提取工具（pdfminer / Docling / MinerU）現在不用裝。** 需要時 `uv` 會即時取用。
> 只有在你要處理**表格特別關鍵**的文獻時，才需要看 [`setup-mineru.md`](setup-mineru.md)。

---

## 2. 第一篇文獻怎麼放？

### 步驟 A：把這個 repo 拿到本機

在 GitHub 頁面按 **Code → Download ZIP**，解壓到你想放知識庫的地方
（例如 `文件/我的藥學知識庫`）。會寫 git 的話 `git clone` 也可以。

### 步驟 B：初始化 `wiki/` 資料夾

剛下載時 `wiki/` 是空的。把兩個空骨架複製進去：

```text
Templates/index.md  →  wiki/index.md
Templates/log.md    →  wiki/log.md
```

用檔案總管複製貼上就行。`index.md` 是全庫目錄，`log.md` 是異動日誌，之後都由 LLM 自動維護，
**你不需要手動編輯**。

### 步驟 C：把 PDF 放進 `raw/`

```text
raw/
└── rybak2020-vancomycin-consensus.pdf
```

**檔名建議用「作者年份-主題」的英文格式**，中文檔名和空格在命令列裡容易出狀況。

`raw/` 已經被 `.gitignore` 排除，PDF 永遠不會被上傳（見第 4 節）。

### 步驟 D：在正確的位置啟動 Claude Code

終端機**切換到知識庫資料夾**再啟動，否則 Claude Code 讀不到 `CLAUDE.md` 這份操作規範：

```bash
cd "文件/我的藥學知識庫"
claude
```

---

## 3. 我要怎麼對 Claude Code 下指令？

**用中文講人話就好。** 這套流程只有三個動作，各對應一句話。

### Ingest（把文獻收進知識庫）

```text
請處理 raw/rybak2020-vancomycin-consensus.pdf
```

Claude Code 會讀 PDF、判定來源型別（RCT / meta-analysis / guideline…）、依型別填 EBM 欄位、
建立 source 摘要頁、順帶新建或更新相關的藥物（entity）與概念（concept）頁並互相連結，
最後更新 `index.md` 與 `log.md`。

**一次 ingest 通常會動到 5–15 個頁面**——這是正常的，不是失控。

做完它會回報：

```text
已建立 N 頁，更新 M 頁，標記矛盾 K 處；lint 結果：通過 / 未通過 / 未執行，請確認
```

> 中途它可能會跟你討論 2–3 個核心發現，或問你某個結論該不該建成獨立頁面。**這是設計的一部分**，
> 你的臨床判斷比 LLM 準。

### Query（問問題）

```text
請問 vancomycin 的 AUC 監測在腎功能不全病人要怎麼調整？
```

它會先讀 `index.md` 找到相關頁面，精讀後合成答案，並附上頁面引用。若答案有保存價值，
它會問你要不要存成一頁 query 頁。

### Lint（健檢）

```text
請做 lint
```

見下一節。

---

## 4. 如何確認沒有錯、沒有洩漏資料？

這是**兩個不同的問題**，分開處理。

### （A）確認品質：跑 lint

在知識庫根目錄的終端機執行：

```bash
uv run --with pyyaml python tools/wiki_lint.py
```

它會產生一份報告 `output/lint-YYYY-MM-DD.md`，並在畫面上印出一段數字摘要。
**你只需要看這幾個數字，全部應該是 0：**

| 數字 | 不是 0 代表 |
|------|------------|
| `pii` | **偵測到疑似未遮罩的個資**——最優先處理，見下方 (B) |
| `broken` | 有連結指向不存在的頁面 |
| `fm_missing` | 有頁面缺 title / type / created 等必要欄位 |
| `ebm_missing_study` | 單篇研究的頁面缺 EBM 欄位（PICO、GRADE…） |
| `ebm_undetermined` | 有頁面的 Study design 欄沒寫清楚，腳本無法判定型別 |
| `sparse` | 有頁面內容過少（正文不到 500 字） |

看到非 0 不用自己修——**把數字貼回去跟 Claude Code 說「lint 有 N 個 X，請修」** 就行。

> `stale` / `hash_untracked` 這兩項跟原始 PDF 是否變動有關，新手可以先忽略。

lint 只做**機械檢查**。它抓得到壞連結，抓不到「這段劑量寫錯了」。所以：

> ### ⚠️ 臨床內容必須由你回核原文
>
> 劑量、交互作用、禁忌、給付規定——LLM 產生的數字**一律回核原始文獻與仿單**再使用。
> 頁面上標著 `[資訊不足]` 或 `[需驗證]` 的地方，就是它自己也不確定的地方。

### （B）確認沒洩漏：三道防線

**第一道：lint 的 PII 掃描。** 腳本會用檢核碼驗證台灣身分證字號，另外抓手機號碼與 email，
報告裡會自動遮罩。`pii: 0` 代表沒抓到。

> **但它抓不到姓名和病歷號。** 中文姓名與病歷號沒有可靠的機械特徵，硬抓會產生大量誤報。
> **放進 `raw/` 的文獻若含病患資料，遮罩是你的責任**：姓名寫 `王○明`、病歷號寫 `12****89`。
> 更好的做法是——**個案資料根本不要放進這個知識庫**，這裡是收文獻的地方。

**第二道：`.gitignore` 白名單。** 就算你之後想用 git 備份，預設也**不會**追蹤任何內容：

- `raw/*` — 你的 PDF（受著作權保護）
- `wiki/*` — 你 ingest 出來的所有頁面（是受著作權保護來源的衍生摘要）
- `output/` — lint 報告

**第三道：不要推上 public repo。** 這是最重要也最容易犯的錯。

> ### 🚫 你 ingest 出來的 wiki 內容不可以公開散布
>
> UpToDate、Micromedex、NCCN、各學會指引——這些來源受著作權保護。
> **個人合理使用 ≠ 可以再散布**，即使是你自己改寫的摘要也一樣。
>
> 想用 git 備份知識庫，請開 **private repo**。詳見 [`DISCLAIMER.md`](../DISCLAIMER.md)。

---

## 接下來

- 想調整規則（例如你不在台灣、不看健保給付）：編輯 `CLAUDE.md` 的 §六領域特殊規則。
- 想處理表格很關鍵的文獻：讀 [`setup-mineru.md`](setup-mineru.md)。
- 卡住了：直接問 Claude Code「`CLAUDE.md` 裡的 XXX 是什麼意思？」——它讀得到那份規範。
