# PDF 提取工具安裝指南

臨床論文的關鍵數據多在表格，提取品質直接影響 wiki source 頁的可信度。本指南涵蓋兩個工具：**MinerU**（首選，表格重建佳）與 **pdfminer.six**（備援，快速跨平台）。

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

## 3. pdfminer.six（備援）

MinerU 失敗 / timeout 時使用。快、跨平台，但**無表格結構**（純座標推算），表格數值可信度較低。

```bash
uv run --with pdfminer.six python -c "from pdfminer.high_level import extract_text; \
open('out.txt','w',encoding='utf-8').write(extract_text('<PDF路徑>'))"
```

> **Windows 注意**：`uvx --from pdfminer.six pdf2txt.py` 無效（`.py` 非 Win32 執行檔，exit 193）。
> 必須用上面的 `uv run --with pdfminer.six python -c` 呼叫 API。

用備援工具 ingest 時，在 source 頁的表格數值後標記 `[需 MinerU 驗證]`，待 MinerU 恢復後重跑確認再移除標記。

---

## 4. MinerU timeout 時的清理（Windows）

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
| MinerU | ★★★（CV 重建） | 慢（載入 ML 模型） | ⚠️ Windows 偶 timeout | 正式 ingest（理想狀況） |
| pdfminer.six | ★（純座標） | 快（秒級） | ✅ | MinerU 失敗備援 |

> 部分廠商資料庫的 PDF 有 DRM 保護，任何工具都無法提取文字——此時只能用 LLM 的 Read 工具視覺讀取（若環境支援），或改用其他授權途徑取得內容。
