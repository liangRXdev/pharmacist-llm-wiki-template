# 藥師 LLM 知識庫模板（Pharmacist LLM Wiki Template）

> 一套用 **Claude Code（或任何 LLM Agent）+ Obsidian** 建立、維護個人臨床藥學實證知識庫的**工作流程與 schema**。
> 本 repo 只提供「方法與骨架」，**不含任何臨床內容**——文獻摘要由你自己 ingest 產生。

---

## 這是什麼

把零散的臨床指引、RCT、meta-analysis 文獻，透過標準化流程交由 LLM 摘要成**互相連結的 wiki 頁面**，建立可即時查詢、可稽核、會自我健檢的個人知識庫。

核心特色：
- **三流程 SOP**：Ingest（建頁）/ Query（查詢）/ Lint（健檢）
- **EBM source 頁最低欄位要求**：強制記錄 Study design、PICO、effect size + 95% CI、RoB、GRADE、Applicability、Bottom line
- **雙向連結知識圖譜**：source ↔ entity ↔ concept，可用 Obsidian graph view 瀏覽
- **PDF 提取策略**：MinerU（表格品質佳）→ pdfminer.six（備援）
- **病患資料自動遮罩**＋**異動日誌可稽核**

---

## 知識圖譜長這樣

文獻經 ingest 後，會織成 source ↔ entity ↔ concept 互連的網絡（以下為**示意**，節點皆為佔位範例，不含臨床內容）：

```mermaid
graph LR
  R[("raw/ 原始文獻 PDF")]
  R -->|ingest| S1["source: 文獻 A"]
  R -->|ingest| S2["source: 文獻 B"]
  S1 --> C1(("concept: 機制 / 操作框架"))
  S2 --> C1
  S1 --> E1["entity: 藥物 X"]
  C1 --> E1
  S2 --> E2["entity: 疾病 Y"]
  C1 -. 矛盾標記 .-> C2(("concept: 對照主題"))
  Q{{"query: 提問合成頁"}} --> C1
  Q --> S2
```

> 在 Obsidian 中可用 **Graph View** 即時瀏覽你自己的真實知識圖譜（會隨 ingest 自動長大）。

---

## 目錄結構

```
.
├── CLAUDE.md          # LLM 操作規範（schema）— 使用前替換 <尖括號> 佔位字串
├── DISCLAIMER.md      # 臨床免責 + 著作權聲明（務必閱讀）
├── LICENSE            # 方法/模板採 MIT；你的文獻摘要內容不在授權範圍
├── raw/               # 放你的原始文獻（PDF）；.gitignore 預設不上傳
│   ├── finish/        # 已 ingest 的文獻
│   └── assets/        # 圖片
├── wiki/              # LLM 維護的知識頁面（初始為空）
│   ├── index.md       # 全庫目錄
│   └── log.md         # 異動日誌
├── Templates/         # 各 type 頁面的 frontmatter 模板
└── docs/
    └── setup-mineru.md  # MinerU / pdfminer 安裝指南
```

---

## 快速開始

1. **Fork / 下載** 本 repo，用 Obsidian 開啟資料夾為一個 vault。
2. 編輯 `CLAUDE.md`，替換所有 `<尖括號>` 佔位字串（vault 路徑、MinerU 路徑、日期）。
3. （選用）依 `docs/setup-mineru.md` 安裝 PDF 提取工具。
4. 把第一篇文獻 PDF 放進 `raw/`。
5. 在 vault 目錄啟動 Claude Code，對它說：**「請處理 raw/你的檔名.pdf」**。
6. LLM 會依 schema 建立 source 頁、相關 entity/concept 頁，並更新 index 與 log。
7. 之後可隨時「請問關於 XXX…」（Query）或「請做 lint」（健檢）。

---

## 適用對象

- 臨床藥師、藥學生、EBM 工作者
- 任何想用 LLM 把文獻轉成結構化、可查詢知識庫的醫療專業人員

> 預設規則含健保給付、多語藥物標籤、台灣臨床情境，可依你的國家/制度自行調整 `CLAUDE.md` §六。

---

## ⚠️ 重要限制

- **不可公開散布你 ingest 後的 wiki 內容**：多數來源（指引、UpToDate、Micromedex、NCCN…）受著作權保護，個人合理使用 ≠ 可再散布。詳見 [`DISCLAIMER.md`](DISCLAIMER.md)。
- **LLM 摘要可能含錯誤**：臨床決策前務必回核原始來源。
- 本 repo 之 MIT 授權僅涵蓋 **schema / 流程 / 模板**，不涵蓋你產生的內容。

---

## 致謝 / 貢獻

歡迎以 issue / PR 改進 schema、流程或 PDF 工具策略。請勿在 PR 中包含任何受著作權保護的文獻內容或個人資料。
