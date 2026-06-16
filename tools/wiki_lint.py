#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
wiki_lint.py — 個人臨床藥學 LLM wiki 健康檢查腳本
依 CLAUDE.md schema 設計，涵蓋 6 項機械檢查 + 圖譜指標 + source 頁 EBM 欄位檢查。

用法：
  uv run --with pyyaml python tools/wiki_lint.py
  uv run --with pyyaml python tools/wiki_lint.py --wiki wiki --raw raw --out output
  uv run --with pyyaml python tools/wiki_lint.py --json     # 只印 JSON 摘要，不寫報告

設計原則：只做「機械可判定」的檢查；矛盾/語意問題仍由 LLM lint 處理。
"""
import os, re, sys, glob, json, argparse, datetime

try:
    import yaml
except ImportError:
    print("需要 pyyaml：請用  uv run --with pyyaml python tools/wiki_lint.py", file=sys.stderr)
    sys.exit(1)

# ---- 設定 ----
REQUIRED_FM = ["title", "type", "tags", "created", "updated"]   # 所有頁面必備 frontmatter
SOURCE_FM_EXTRA = ["sources"]                                    # source 頁額外必備
# EBM 欄位分型（CLAUDE.md §六）：單篇研究頁查 FULL，guideline/共識/工具/法規/衛教查 LIGHT
# 每欄接受中英別名（任一出現即視為存在）
EBM_ALIASES = {
    "Study design": ["study design", "研究設計", "文件性質", "來源型別", "文件型別", "文件類型"],
    "PICO": ["pico"],
    "Primary outcome": ["primary outcome", "主要結果", "主要終點", "主要複合終點"],
    "Secondary outcomes": ["secondary outcome", "次要結果", "次要終點"],
    "RoB": ["rob", "risk of bias", "偏誤風險", "偏倚風險"],
    "GRADE": ["grade"],
    "Applicability": ["applicability", "適用性", "台灣適用", "台灣臨床重點",
                      "台灣特殊考量", "台灣重點", "台灣臨床", "在台"],
    "Bottom line": ["bottom line", "單句結論", "臨床結論", "一句話結論"],
}
EBM_FULL = list(EBM_ALIASES.keys())
EBM_LIGHT = ["Study design", "Applicability", "Bottom line"]
# 研究型判定（出現於 Study design 欄即視為單篇研究 → 查 EBM_FULL）
STUDY_KW = ["rct", "randomi", "randomized", "cohort", "case-control", "case control",
            "meta-analysis", "meta analysis", "pooled", "post hoc", "post-hoc",
            "cross-sectional", "observational", "隨機", "世代", "病例對照",
            "統合分析", "前瞻", "回溯", "觀察性", "次級分析"]
# 非研究型線索（guideline/共識/工具/法規/衛教）→ 查 EBM_LIGHT
NONSTUDY_KW = ["guideline", "指引", "consensus", "共識", "cpic", "criteria", "準則",
               "beers", "stopp", "start", "清單", "prohibited list", "list",
               "手冊", "manual", "education", "衛教", "量表", "scale", "standards of care",
               "建議", "recommendation", "專書", "照護"]
SPARSE_CHARS = 500          # 正文非空白字元數低於此 → 稀疏
META_NODES = {"index", "log", "MEMORY", "README"}  # 不計入孤立/指標的 meta 檔
LINK_RE = re.compile(r"\[\[\s*(?:wiki/)?([^\]\|#]+?)\s*(?:\|[^\]]*)?\]\]")
RAW_LINK_RE = re.compile(r"\[\[\s*raw/([^\]\|#]+?)\s*(?:\|[^\]]*)?\]\]")


def parse_page(path):
    base = os.path.splitext(os.path.basename(path))[0]
    txt = open(path, encoding="utf-8").read()
    fm, body = {}, txt
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", txt, re.S)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            fm = {"_parse_error": True}
        body = m.group(2)
    # 連結（排除 raw/）
    targets = set()
    for mm in LINK_RE.finditer(txt):
        t = mm.group(1).strip()
        if not t.startswith("raw/"):
            targets.add(t)
    body_chars = len(re.sub(r"\s", "", body))
    return {"name": base, "fm": fm, "body": body, "targets": targets,
            "body_chars": body_chars, "path": path}


def find_raw(sources, raw_dir):
    """回傳 [(source_name, mtime or None)]，在 raw/ 遞迴搜尋（含 finish/、Literature/）。"""
    found = []
    search_dirs = [raw_dir]
    lit = os.path.join(os.path.dirname(raw_dir), "Literature")
    if os.path.isdir(lit):
        search_dirs.append(lit)
    for s in sources:
        stem = os.path.splitext(str(s))[0]
        hit = None
        for d in search_dirs:
            for root, _, files in os.walk(d):
                for f in files:
                    if os.path.splitext(f)[0] == stem or f == str(s):
                        hit = os.path.join(root, f)
                        break
                if hit:
                    break
            if hit:
                break
        found.append((str(s), os.path.getmtime(hit) if hit else None))
    return found


def to_date(v):
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, str):
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", v)
        if m:
            return datetime.date(int(m[1]), int(m[2]), int(m[3]))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--raw", default="raw")
    ap.add_argument("--out", default="output")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = os.getcwd()
    wiki_dir = os.path.join(root, args.wiki)
    raw_dir = os.path.join(root, args.raw)
    files = glob.glob(os.path.join(wiki_dir, "*.md"))
    pages = {p["name"]: p for p in (parse_page(f) for f in files)}
    names = set(pages)
    content = {n: p for n, p in pages.items() if n not in META_NODES}

    # ---- 連結圖 ----
    inbound = {n: set() for n in names}
    edges = 0
    for src, p in pages.items():
        for t in p["targets"]:
            edges += 1
            if t in inbound:
                inbound[t].add(src)

    # 1. 壞鏈
    broken = []
    for src, p in pages.items():
        for t in p["targets"]:
            if t not in names and t not in META_NODES:
                broken.append((src, t))
    broken = sorted(set(broken))

    # 2. 孤立頁（content 頁無任何 content inbound；忽略 meta 來源）
    orphans = sorted(n for n in content
                     if not (inbound[n] - META_NODES))

    # 3. 單向連結（content↔content：A→B 但 B↛A）
    one_way = []
    for src, p in pages.items():
        if src in META_NODES:
            continue
        for t in p["targets"]:
            if t in content and src not in pages[t]["targets"]:
                one_way.append((src, t))
    one_way = sorted(set(one_way))
    reciprocated = sum(1 for s, p in content.items()
                       for t in p["targets"]
                       if t in content and s in pages[t]["targets"])
    cc_edges = sum(1 for s, p in content.items() for t in p["targets"] if t in content)

    # 4. 稀疏頁
    sparse = sorted([(n, p["body_chars"]) for n, p in content.items()
                     if p["body_chars"] < SPARSE_CHARS], key=lambda x: x[1])

    # 5. frontmatter 缺欄
    fm_missing = []
    for n, p in content.items():
        req = REQUIRED_FM + (SOURCE_FM_EXTRA if p["fm"].get("type") == "source" else [])
        miss = [k for k in req if not p["fm"].get(k)]
        if p["fm"].get("_parse_error"):
            miss.append("(frontmatter 解析失敗)")
        if miss:
            fm_missing.append((n, miss))
    fm_missing.sort()

    # 5b. source 頁 EBM 欄位（依來源型別查 FULL 或 LIGHT）
    ebm_missing = []   # 研究頁缺 EBM_FULL（真缺口）
    ebm_light_missing = []  # 非研究頁缺 EBM_LIGHT
    n_study = n_guideline = 0
    for n, p in content.items():
        if p["fm"].get("type") != "source":
            continue
        body_l = p["body"].lower()
        sd = ""
        sm = re.search(r"study design[^\n|]*[|:：]\s*([^\n|]+)", p["body"], re.I)
        if sm:
            sd = sm.group(1).lower()
        title_l = str(p["fm"].get("title", "")).lower() + " " + n.lower()
        is_study = any(k in sd for k in STUDY_KW)
        is_nonstudy = any(k in sd for k in NONSTUDY_KW) or any(k in title_l for k in NONSTUDY_KW)
        # 研究關鍵字優先；兩者皆無 → 預設 guideline（保守，不強逼 PICO）
        def field_missing(field):
            if field == "PICO":
                if "pico" in body_l:
                    return False
                # 結構式 P/I/C/O（表格列或粗體標記，如 | **P** | ...）
                pcs = set(re.findall(r"\*\*\s*([PICO])\s*\*\*", p["body"]))
                return not pcs >= {"P", "I", "C", "O"}
            return not any(a in body_l for a in EBM_ALIASES[field])
        if is_study and not is_nonstudy:
            n_study += 1
            miss = [f for f in EBM_FULL if field_missing(f)]
            if miss:
                ebm_missing.append((n, miss))
        else:
            n_guideline += 1
            miss = [f for f in EBM_LIGHT if field_missing(f)]
            if miss:
                ebm_light_missing.append((n, miss))
    ebm_missing.sort()
    ebm_light_missing.sort()

    # 6. 過期頁（raw 來源 mtime > 頁面 updated）
    stale = []
    for n, p in content.items():
        srcs = p["fm"].get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]
        upd = to_date(p["fm"].get("updated"))
        if not srcs or not upd:
            continue
        for sname, mt in find_raw(srcs, raw_dir):
            if mt and datetime.date.fromtimestamp(mt) > upd:
                stale.append((n, sname, datetime.date.fromtimestamp(mt).isoformat(), upd.isoformat()))
    stale.sort()

    # ---- 指標 ----
    nC = len(content) or 1
    metrics = {
        "頁面總數": len(files),
        "content 頁數": len(content),
        "孤立率": f"{len(orphans)/nC*100:.1f}%",
        "壞鏈率": f"{len(broken)/(edges or 1)*100:.1f}%",
        "平均出鏈": f"{sum(len(p['targets']) for p in content.values())/nC:.1f}",
        "雙向率": f"{reciprocated/(cc_edges or 1)*100:.1f}%",
    }
    targets_ok = {
        "孤立率": ("< 5%", len(orphans)/nC < 0.05),
        "壞鏈率": ("< 2%", len(broken)/(edges or 1) < 0.02),
        "平均出鏈": ("≥ 5", sum(len(p['targets']) for p in content.values())/nC >= 5),
        "雙向率": ("≥ 50%", reciprocated/(cc_edges or 1) >= 0.5),
    }
    # type 分布
    type_dist = {}
    for p in content.values():
        type_dist[p["fm"].get("type", "(無)")] = type_dist.get(p["fm"].get("type", "(無)"), 0) + 1

    summary = {"metrics": metrics, "broken": len(broken), "orphans": len(orphans),
               "one_way": len(one_way), "sparse": len(sparse),
               "fm_missing": len(fm_missing),
               "ebm_missing_study": len(ebm_missing), "ebm_missing_guideline": len(ebm_light_missing),
               "source_study": n_study, "source_guideline": n_guideline,
               "stale": len(stale)}

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    # ---- 寫報告 ----
    today = datetime.date.today().isoformat()
    L = []
    L.append(f"# Wiki Lint 報告 — {today}\n")
    L.append("> 由 `tools/wiki_lint.py` 自動產生（機械檢查）。矛盾/語意問題仍需 LLM lint。\n")

    L.append("## 圖譜指標\n")
    L.append("| 指標 | 數值 | 目標 | 狀態 |")
    L.append("|------|------|------|------|")
    for k, v in metrics.items():
        if k in targets_ok:
            tgt, ok = targets_ok[k]
            L.append(f"| {k} | {v} | {tgt} | {'✅' if ok else '⚠️'} |")
        else:
            L.append(f"| {k} | {v} | — | — |")
    L.append("")
    L.append("type 分布：" + "、".join(f"{k} {v}" for k, v in sorted(type_dist.items(), key=lambda x: -x[1])) + "\n")

    def section(title, items, fmt, empty="無"):
        L.append(f"## {title}（{len(items)}）\n")
        if not items:
            L.append(f"- {empty}\n")
            return
        for it in items:
            L.append(fmt(it))
        L.append("")

    section("🔴 壞鏈（target 不存在）", broken, lambda x: f"- `{x[0]}` → [[{x[1]}]]")
    section("🟠 孤立頁（無 content inbound）", orphans, lambda x: f"- {x}")
    section("🟠 frontmatter 缺欄", fm_missing, lambda x: f"- `{x[0]}`：缺 {', '.join(x[1])}")
    L.append(f"> EBM 分型：研究型 source {n_study} 頁（查 8 欄）、guideline/工具型 {n_guideline} 頁（查輕量 3 欄）\n")
    section("🔴 研究型 source 缺 EBM 欄位（真缺口，應補）", ebm_missing,
            lambda x: f"- `{x[0]}`：缺 {', '.join(x[1])}")
    section("🟡 guideline/工具型 source 缺輕量欄位（Study design/Applicability/Bottom line）", ebm_light_missing,
            lambda x: f"- `{x[0]}`：缺 {', '.join(x[1])}")
    section("🟡 過期頁（raw 來源比 updated 新）", stale,
            lambda x: f"- `{x[0]}`：來源 {x[1]} (mtime {x[2]}) > updated {x[3]}")
    section(f"🟡 稀疏頁（正文 < {SPARSE_CHARS} 字）", sparse, lambda x: f"- `{x[0]}`（{x[1]} 字）")
    # 單向連結量大，僅報數量 + 取樣
    L.append(f"## ℹ️ 單向連結（content↔content，A→B 但 B↛A）（{len(one_way)}）\n")
    L.append("> 並非全部都該雙向；僅供人工挑選補回鏈。以下取樣前 30 筆：\n")
    for s, t in one_way[:30]:
        L.append(f"- `{s}` → `{t}`")
    if len(one_way) > 30:
        L.append(f"- …其餘 {len(one_way)-30} 筆略")
    L.append("")

    os.makedirs(os.path.join(root, args.out), exist_ok=True)
    outpath = os.path.join(root, args.out, f"lint-{today}.md")
    open(outpath, "w", encoding="utf-8").write("\n".join(L))
    print(f"報告已寫入：{outpath}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
