# PDF 提取工具策略（選型與失敗處理）

> **本檔講「何時用哪個工具」；[`setup-mineru.md`](setup-mineru.md) 講「怎麼裝」。**
> 手上有一份要 ingest 的 PDF 時讀本檔。
>
> `CLAUDE.md` §七只留一條常駐警告（Docling 整份大檔會 `bad_alloc` 並可能拖垮整機），
> 其餘細節在這裡。

---

## 1. Ingest 用途（建立 source 頁）

**首選工作流：分工＝pdfminer 全文正文 + Docling 逐表（關鍵表格）。**
MinerU 退為「需整檔一次出、可接受黏字」的次選。

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

- **Docling `bad_alloc`**（整份崩潰）→ 確認背景進程已死 → 改切更小檔逐表
  → 仍失敗則該表退 MinerU 或 pdfminer + 對照原文手動建表。
- **MinerU 啟動失敗 / 殭屍進程** → 清殭屍 python 進程後重試，或改用 Docling（切小檔）抽表。
- **兩者皆失敗** → pdfminer 抽全文正文；表格數值標記 `[需 Docling/MinerU 驗證]`，
  待工具正常後重跑該表確認。

---

## 3. 快速查詢（非 ingest）

直接用 Read 工具讀 PDF（`pages` 參數分段）。若環境無 `pdftoppm` 致無法讀 PDF，
先用 pdfminer 提取文字再 Read `.txt`。
