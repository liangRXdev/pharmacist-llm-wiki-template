# PDF 提取工具策略（選型與失敗處理）

> **本檔講「何時用哪個工具」；[`setup-mineru.md`](setup-mineru.md) 講「怎麼裝」。**
> 手上有一份要 ingest 的 PDF 時讀本檔。
>
> `CLAUDE.md` §七只留一條常駐警告（Docling 整份大檔會 `bad_alloc` 並可能拖垮整機），
> 其餘細節在這裡。

---

## 0. 先分流（拿到任何 PDF 的第一件事）

先用 **pdf-inspector**（Rust，無 ML／無 OCR／無雲端 API）跑一次分類，<5 秒拿到
`page_count`、`pages_with_tables`、`has_encoding_issues`，據此決定後面怎麼走。

```bash
uv run --with pdf-inspector python -c "
import pdf_inspector as pi
r = pi.process_pdf('<PDF路徑>')
print(r.pdf_type, r.page_count, r.pages_with_tables, r.has_encoding_issues)
open('out.md','w',encoding='utf-8').write(r.markdown)"
```

> Python 套件**不提供 CLI entrypoint**（`uv tool install` 會失敗），只能用 Python API。
> `pages_with_tables` 為 **1-based**。

| 分流結果 | 走法 |
|---------|------|
| **`pages_with_tables` 為空** | **不用碰 Docling**，pdfminer 正文即收工 |
| **一般期刊論文**（≲30 頁、雙欄） | 正文 **pdfminer**（pdf-inspector 在窄欄兩端對齊會掉字間空格）；表格頁交 **Docling** |
| **大型指引**（≳50 頁，多為 Word 產生） | 正文＋標題階層 **pdf-inspector**（Docling 整檔會 `bad_alloc`、pdfminer 無標題）；**只把關鍵閾值表**交 Docling |
| 任一情況 | `pages_with_tables` **取代** §1(B) Step 0「猜表中獨特字串再 pypdf grep」 |

**pdfminer 的 `.txt` 一律照產**——查更正啟事（`Corrected on` / `Erratum`）與正文交叉比對都靠它。

> [!warning] pdf-inspector 只在**分流**與**大型指引正文**這兩件事上可信
> 它有**兩個安靜的失敗模式**（exit 0、不報錯、輸出看起來正常）：
> 1. **窄欄兩端對齊正文 → 掉字間空格**（實測：同一工具在雙欄期刊論文的黏字率是 pdfminer 的
>    **上百倍**，但在 Word 產生的指引上兩者**完全相同** → 是排版特有失敗，不是工具整體差）
> 2. **多欄表格 → 整表塌成單格，或上標註腳編號被黏到數值「前面」**
>
> 第 2 種最危險，因為**數值全部正確、只有註腳位置錯，看起來完全正常**：
>
> | 正確 | pdf-inspector |
> |---|---|
> | `≤2 ᵃ` | `a ≤2` |
> | `≤16 ᵇ` | `b ≤16` |
>
> 若該欄是**臨床閾值**（藥敏 breakpoint、劑量上限、診斷切點），`a ≤2` 究竟是 a 還是 ≤2
> 會直接改變判讀。
> **判別訊號：儲存格出現「裸字元＋空格＋≤/≥」。**
>
> **⇒ 硬規則：任何要寫進頁面的臨床數值表，一律出自 Docling，不得採用 pdf-inspector 的表格輸出。**

> [!note] 不要被它的官方 benchmark 誤導
> pdf-inspector 的公開 benchmark 在 tables 一項分數很高，但其語料以**一般文件**為主。
> 臨床知識庫需要的是「期刊多欄密集數值表逐格正確」，恰好落在它塌掉的那一類。
> **選工具要看它在你的失敗模式上的表現，不是平均分。**

---

## 1. Ingest 用途（建立 source 頁）

**首選工作流：分工＝pdfminer 全文正文 + Docling 逐表（關鍵表格）。**
MinerU 退為「需整檔一次出、可接受黏字」的次選。
**大型指引例外**：正文＋標題階層改用 pdf-inspector（見 §0）。

### (A) 正文：pdfminer.six

敘述/建議分級等文字段落，抽全文後 Read `.txt`（快、跨平台、穩定）：

```bash
uv run --with pdfminer.six python -c "from pdfminer.high_level import extract_text; \
open('out.txt','w',encoding='utf-8').write(extract_text('<PDF路徑>'))"
```

> Windows 注意：`uvx --from pdfminer.six pdf2txt.py` 無效（`.py` 非 Win32 執行檔）；
> 須用 `uv run --with pdfminer.six python -c` 呼叫 API。

### (B) 關鍵臨床表格：Docling（切小檔逐表）★ 表格品質最佳

- **優點**：原生輸出 GFM markdown 表（可直接貼入 wiki）、欄列分明、字元與臨床閾值準確
  （實測勝 MinerU 的黏字、字母混淆、閾值污染）。
- **適合時機**：劑量表、不良反應表、診斷閾值表、治療決策矩陣、**多模型敏感度分析表**等高精度表。
- **限制**：CLI 多無 `--page-range`；整份大型 PDF（>~50 頁）會累積記憶體爆掉（`std::bad_alloc`）
  並可能拖垮整機 → **務必先用 pypdf 切小檔（每檔 3–5 頁，只含目標表格頁）再逐檔跑**；
  輸出表後常嵌 base64 圖片字串，以 `grep -v "data:image"` 剝除；模型載入較慢。

> [!important] **何時必須切表給 Docling**（判斷徵兆，不是憑感覺）
> 當 pdfminer 抽出的數字**逐一正確、但欄列對應被打散**時。典型症狀：`grep` 到一串裸數值
> （`0.86 (0.72 to 0.98)`、`0.91 (0.85 to 0.97)`…）卻**無法判斷哪個屬於哪一列/哪一欄**。
>
> 此時若「照抄摘要的那個數字」，就會把**敏感度分析誤當成主要分析**——而指引引用的
> 往往正是敏感度分析那一列。這種錯誤不會被任何 lint 抓到。
> 相關規則見 [`evidence-discipline.md`](evidence-discipline.md) (a)。

```bash
# Step 0：先定位表格在第幾頁（不必先跑 MinerU）
uv run --with pypdf python -c "from pypdf import PdfReader; r=PdfReader('<PDF>'); [print('page_idx',i) for i,p in enumerate(r.pages) if '<表中獨特字串>' in (p.extract_text() or '')]"
# Step 1：pypdf 切目標表格頁（0-based index）
uv run --with pypdf python -c "from pypdf import PdfReader,PdfWriter; r=PdfReader('<PDF>'); w=PdfWriter(); [w.add_page(r.pages[i]) for i in range(<起>,<迄>+1)]; w.write(open('split.pdf','wb'))"
# Step 2：對小檔跑 Docling
docling split.pdf --to md --output <輸出目錄> --table-mode accurate
```

### (C) MinerU：整檔一次轉換（次選/備援）

安裝與指令見 [`setup-mineru.md`](setup-mineru.md)。其 `_content_list.json` 可快速定位每張表的頁碼
（即使整份表格品質不佳，仍可用於決定 Docling 要切哪幾頁）。

HTML 表格殘餘問題：相鄰列合併、黏字、字母混淆（II↔Il）、CI 截斷 → 對照正文修正。

---

## 2. 失敗時的備援邏輯

### 失敗模式 A：Docling `bad_alloc`（整份大檔崩潰）

確認背景進程已死 → 改切更小檔逐表 → 仍失敗則該表退 MinerU 或 pdfminer + 對照原文手動建表。
`--page-batch-size` 之類的旗標**救不了**整份累積爆量。

### 失敗模式 A2：Docling 跑完但表格重建錯（**不報錯，最危險**）

**症狀**：`exit 0`、有輸出、**無任何錯誤訊息**，但欄位併進單一儲存格／列頭錯位／**整表轉置**。
**根因**：**跨頁寬表或橫向（landscape）版面** —— 這是**版面重建問題，不是記憶體問題**
→ **切小檔與單頁重試都無效**。

> [!warning] A 與 A2 的關鍵區別
> A 會噴錯並拖垮整機；**A2 安靜地給你一張看起來像表格的錯誤資料**。

**跑之前就能預判**：

| 訊號 | 判斷 |
|------|------|
| 直立表、欄數 ≤ 4–5、跨頁但列方向不變 | ✅ Docling 適用 |
| **橫向版面**或欄數很多（Study/Design/N/Age/Sex/納入/排除/Outcomes/追蹤…） | ❌ 高風險，預期失敗 |
| **SR/meta 的「納入研究特徵表」** | ❌ 幾乎必為寬表 → **直接別試**，走下方搶救法 |

**搶救法：不得硬套，改用正文錨點交叉驗證釘住欄序。**

1. 先確認**正文敘述的數字乾淨**（與 Abstract 交叉驗證）。
2. 在正文找**可對照的錨點**驗證欄序（例如正文寫「樣本數自 77 至 569」，
   若重建結果第 2 欄 N=77 吻合 → 欄序確認）。
3. **只採納被錨點驗證過的數值**，並在頁面標**中等信心**。
4. **未被驗證的欄位一律不寫。** 在 log 與頁面據實記「Docling 部分失敗」。

### 失敗模式 B：MinerU 啟動失敗 / 殭屍進程

清殭屍 python 進程後重試，或改用 Docling（切小檔）抽表。

### 兩者皆失敗

pdfminer 抽全文正文；表格數值標記 `[需 Docling/MinerU 驗證]`，待工具正常後重跑該表確認。

### 三個工具都拿不到的東西

**forest plot 內的 I²／H²、各研究權重、個別研究效果量** —— 它們是**圖片內容**。
→ **後果**：GRADE 的 inconsistency domain 只能記「**未能證實不一致**」，
**不可寫成「已確認同質」**。這是誠實標記的義務，不是可略的細節。

---

## 3. 快速查詢（非 ingest）

直接用 Read 工具讀 PDF（`pages` 參數分段）。若環境無 `pdftoppm` 致無法讀 PDF，
先用 pdfminer 提取文字再 Read `.txt`。

---

## 4. 工具比較

| 工具 | 表格準確度 | 速度 | 適用情境 |
|------|-----------|------|---------|
| **Docling** | ★★★★（**直立表**最佳）／**★（跨頁寬表、橫向版面 → 重建失敗且不報錯）** | 慢（ML 載入；小檔約 1–1.5 min/檔） | **關鍵臨床表格首選**（切 3–5 頁逐表）；**寬表不適用** |
| **pdfminer** | ★（純座標推算；表格不可用） | 快（秒級） | **全文正文首選**；ML 工具失敗時的文字備援 |
| **pdf-inspector** | ★★★★（Word 產生的簡單寬格表）／**★（多欄密集數值表 → 塌陷或註腳位移）** | **極快（無 ML）** | **分流**、**定位表格頁**、**大型指引正文＋標題階層**；**不可用於期刊數值表與窄欄正文** |
| MinerU | ★★★（CV 重建，但黏字／字元錯誤） | 慢（ML 載入） | 整檔一次轉換；`_content_list.json` 可定位表格頁 |
| MarkItDown | ❌ 底層即 pdfminer，字元品質更差 | — | **不建議使用** |

---

*異動：新增 §0 分流表（pdf-inspector 先分流）與其兩個安靜失敗模式；
§2 補上失敗模式 **A2**（跨頁寬表／橫向版面重建失敗且不報錯）與錨點交叉驗證搶救法；
新增 §4 工具比較表。*
