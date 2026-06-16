# PDF 提取工具安裝指南

臨床論文的關鍵數據多在表格，提取品質直接影響 wiki source 頁的可信度。本指南涵蓋三個工具：**pdfminer.six**（全文正文，快速跨平台）、**Docling**（關鍵表格首選，品質最佳）與 **MinerU**（整檔轉換，次選/備援）。

> 首選工作流：**pdfminer 全文正文 + Docling 逐表（切小檔）**。

兩者都建議用 [`uv`](https://github.com/astral-sh/uv) 管理 Python 環境（避免污染系統 Python）。

---

## 1. 安裝 uv

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. MinerU（首選）

MinerU 用電腦視覺重建表格，品質最佳，但需下載 ML 模型、啟動較慢，且在某些 Windows 環境偶有 timeout。

```bash
# 建立獨立環境並安裝
uv venv <你的工具目錄>/mineru-env
uv pip install --python <你的工具目錄>/mineru-env -U "mineru[pipeline]"
```

執行（轉 Markdown）：

```bash
<MINERU_PATH>/mineru -p "<PDF絕對路徑>" -o "<輸出目錄>/mineru" -b pipeline -l en -m auto
```

- 輸出：`<輸出目錄>/mineru/<檔名>/auto/<檔名>.md`
- `-l`：原文語言（`en`、`ch` 等）；中英混排文件實測 `-l en` 對英文藥名/數據較穩
- 在 `CLAUDE.md` 把 `<MINERU_PATH>` 替換為實際執行檔路徑

**常見殘餘問題與處理**：
- 相鄰列合併 → 對照 Results 文字手動拆列
- 特殊符號誤判（森林圖菱形 → emoji）→ 替換為 `◆`
- CI 數值末位截斷 → 對照正文補回

---

## 3. Docling（關鍵臨床表格首選）

表格品質最佳：原生輸出 GFM markdown 表（可直接貼入 wiki）、欄列分明、字元與臨床閾值準確（實測勝 MinerU 的黏字/字母混淆/閾值污染）。

```bash
uv tool install docling      # 或 uv run --with docling docling ...
```

**限制與用法**：CLI 多無 `--page-range`，整份大型 PDF（>~50 頁）會累積記憶體爆掉（`std::bad_alloc`）並可能拖垮整機 → **務必先用 pypdf 切小檔（每檔 3–5 頁，只含目標表格頁）再逐檔跑**。

```bash
# Step 1：pypdf 切目標表格頁（0-based index；可用 MinerU 的 _content_list.json 定位頁碼）
uv run --with pypdf python -c "from pypdf import PdfReader,PdfWriter; r=PdfReader('<PDF>'); w=PdfWriter(); [w.add_page(r.pages[i]) for i in range(<起>,<迄>+1)]; w.write(open('split.pdf','wb'))"
# Step 2：對小檔跑 Docling（--table-mode accurate）
docling split.pdf --to md --output <輸出目錄> --table-mode accurate
```

> 輸出表後常嵌 base64 圖片字串 → 萃取表格時以 `grep -v "data:image"` 剝除。

---

## 4. pdfminer.six（全文正文 / 備援）

抽取全文純文字用於 source 頁正文（敘述、建議分級）。快、跨平台，但**無表格結構**（純座標推算）→ 表格不可用。

```bash
uv run --with pdfminer.six python -c "from pdfminer.high_level import extract_text; \
open('out.txt','w',encoding='utf-8').write(extract_text('<PDF路徑>'))"
```

> **Windows 注意**：`uvx --from pdfminer.six pdf2txt.py` 無效（`.py` 非 Win32 執行檔，exit 193）。
> 必須用上面的 `uv run --with pdfminer.six python -c` 呼叫 API。

Docling/MinerU 皆失敗時，以 pdfminer 抽正文，表格數值後標記 `[需 Docling/MinerU 驗證]`，待工具恢復後重跑該表確認再移除標記。

---

## 5. MinerU timeout 時的清理（Windows）

若反覆 timeout，可能有殘留 python 殭屍進程佔記憶體：

```powershell
Get-Process | Where-Object { $_.Name -like "*python*" } |
  Select-Object Id, Name, @{N='Mem_MB';E={[math]::Round($_.WorkingSet/1MB,0)}}
# 結束低記憶體（< 100 MB）的殘留進程：
Stop-Process -Id <PID> -Force
```

---

## 工具比較

| 工具 | 表格準確度 | 啟動速度 | 跨平台 | 適用情境 |
|------|-----------|---------|--------|---------|
| **Docling** | ★★★★（GFM 表、閾值/字元準） | 慢（載入 ML 模型）；小檔約 1–1.5 min | ✅（**須切小檔**） | **關鍵臨床表格首選**（pypdf 切 3–5 頁逐表） |
| MinerU | ★★★（CV 重建，偶黏字/字元錯誤） | 慢（載入 ML 模型） | ⚠️ Windows 偶 timeout | 整檔一次轉換；用 `_content_list.json` 定位表格頁 |
| pdfminer.six | ★（純座標；表格不可用） | 快（秒級） | ✅ | 全文正文首選；表格工具失敗時文字備援 |

> ⚠️ Docling 整份大檔會 `std::bad_alloc` 崩潰（無 `--page-range`）→ 務必先 pypdf 切小檔逐表。

> 部分廠商資料庫的 PDF 有 DRM 保護，任何工具都無法提取文字——此時只能用 LLM 的 Read 工具視覺讀取（若環境支援），或改用其他授權途徑取得內容。
