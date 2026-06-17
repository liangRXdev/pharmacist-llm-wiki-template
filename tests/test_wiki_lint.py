# -*- coding: utf-8 -*-
"""
tests/test_wiki_lint.py — wiki_lint.py 回歸測試骨架

執行：
    uv run --with pyyaml --with pytest pytest -q
    # 或： pip install pyyaml pytest && pytest -q

三組案例：
    1. PII / 身分證檢核碼   → 純函式單元測試（import valid_twid / scan_pii）
    2. hash 過期            → 端對端（subprocess + --json），含 YAML-int 與 raw/ 前綴回歸
    3. EBM 型別分類          → 端對端，驗證 study / guideline / 型別待確認 三分流

設計說明：
    - 純函式（valid_twid 等）直接 import 測，快又精準。
    - EBM 分類與 hash 過期邏輯目前內聯在 main()，故以 subprocess 跑 --json、解析摘要 dict 來測。
      若日後把這兩段抽成可 import 的函式，可改寫成更細的單元測試（見檔尾 TODO）。
"""
import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path

import pytest

# ---- 路徑與 import ----
REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "tools" / "wiki_lint.py"
sys.path.insert(0, str(REPO / "tools"))
import wiki_lint  # noqa: E402  (valid_twid / scan_pii / mask_pii / file_sha256)


# ============================================================
#  共用工具
# ============================================================
def write_vault(tmp_path, pages: dict, raw: dict | None = None):
    """在 tmp_path 下建立 wiki/ 與 raw/，寫入頁面與原始檔。
    pages: {頁名: markdown字串}; raw: {檔名: bytes}。回傳 tmp_path。"""
    (tmp_path / "wiki").mkdir()
    (tmp_path / "raw").mkdir()
    for name, body in pages.items():
        (tmp_path / "wiki" / f"{name}.md").write_text(body, encoding="utf-8")
    for fname, data in (raw or {}).items():
        (tmp_path / "raw" / fname).write_bytes(data)
    return tmp_path


def run_lint(vault: Path) -> dict:
    """以 vault 為 cwd 跑 wiki_lint.py --json，回傳解析後的摘要 dict。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        cwd=str(vault), capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"lint 非零退出：\n{proc.stderr}"
    return json.loads(proc.stdout)


def page(front: dict, body: str) -> str:
    """組出 frontmatter + 正文的 markdown。front 的值原樣寫入（含未引號數字測試）。"""
    lines = ["---"]
    for k, v in front.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append(body)
    return "\n".join(lines)


FM_BASE = {
    "title": "test",
    "type": "source",
    "tags": "[t]",
    "created": "2026-06-01",
    "updated": "2026-06-01",
}


def find_numeric_hash_content():
    """確定性地找出一段內容，使其 file_sha256()（sha256 前 16 碼）全為數字。
    用於回歸測試「YAML 把全數字雜湊載成 int」的 str() 強制轉型修補。"""
    for i in range(500_000):
        data = str(i).encode()
        h = hashlib.sha256(data).hexdigest()[:16]
        if h.isdigit():
            return data, h
    pytest.skip("找不到全數字雜湊內容（理論上不會發生）")


# ============================================================
#  Group 1 — 身分證檢核碼 / PII 掃描（純函式）
# ============================================================
class TestPIIChecksum:
    def test_valid_twid_true(self):
        # A123456789 為合法檢核碼
        assert wiki_lint.valid_twid("A", "123456789") is True

    def test_invalid_twid_checksum_false(self):
        # 末碼錯一位 → 檢核碼不過
        assert wiki_lint.valid_twid("A", "123456788") is False

    def test_unknown_letter_false(self):
        assert wiki_lint.valid_twid("?", "123456789") is False

    @pytest.mark.parametrize("letter", list("ABCDEFGHJKLMNPQRSTUVXYWZIO"))
    def test_letter_table_complete(self, letter):
        # 每個合法字首都應有對應碼（不應 KeyError/None 例外路徑）
        assert wiki_lint._TWID_LETTER.get(letter) is not None

    def test_scan_pii_detects_valid_id_masked(self):
        hits = wiki_lint.scan_pii("病患 A123456789 入院")
        kinds = [k for k, _ in hits]
        assert "台灣身分證" in kinds
        # 報告樣本必須已遮罩，不得含原值
        assert all("123456789" not in sample for _, sample in hits)

    def test_scan_pii_ignores_invalid_checksum(self):
        hits = wiki_lint.scan_pii("代碼 A123456788 僅為流水號")
        assert all(k != "台灣身分證" for k, _ in hits)

    def test_scan_pii_detects_phone_and_email(self):
        hits = wiki_lint.scan_pii("聯絡 0912345678 或 a.wang@hosp.org.tw")
        kinds = {k for k, _ in hits}
        assert {"手機號碼", "Email"} <= kinds

    def test_scan_pii_silent_on_masked_or_mrn(self):
        # 已遮罩身分證、與「病歷號」這類無高精度 pattern 者 → 不應命中
        hits = wiki_lint.scan_pii("已遮罩 A12****90；病歷號 12****89")
        assert hits == []


# ============================================================
#  Group 2 — hash 過期偵測（端對端）
# ============================================================
class TestHashStaleness:
    RAW = {"trialA.pdf": b"content-v1"}

    def _hash(self):
        return hashlib.sha256(self.RAW["trialA.pdf"]).hexdigest()[:16]

    def test_correct_hash_not_stale(self, tmp_path):
        fm = {**FM_BASE, "sources": "[trialA.pdf]", "source_hash": self._hash()}
        v = write_vault(tmp_path, {"s": page(fm, "| Study design | RCT |")}, self.RAW)
        out = run_lint(v)
        assert out["stale"] == 0
        assert out["hash_untracked"] == 0

    def test_wrong_hash_is_stale(self, tmp_path):
        fm = {**FM_BASE, "sources": "[trialA.pdf]", "source_hash": "deadbeefdeadbeef"}
        v = write_vault(tmp_path, {"s": page(fm, "| Study design | RCT |")}, self.RAW)
        assert run_lint(v)["stale"] == 1

    def test_missing_hash_is_untracked_not_stale(self, tmp_path):
        fm = {**FM_BASE, "sources": "[trialA.pdf]"}  # 無 source_hash
        v = write_vault(tmp_path, {"s": page(fm, "| Study design | RCT |")}, self.RAW)
        out = run_lint(v)
        assert out["stale"] == 0
        assert out["hash_untracked"] == 1

    def test_raw_prefix_in_sources_still_matches(self, tmp_path):
        # 回歸：sources 寫成 raw/trialA.pdf（schema 慣例）也要對到 raw/trialA.pdf
        fm = {**FM_BASE, "sources": "[raw/trialA.pdf]", "source_hash": self._hash()}
        v = write_vault(tmp_path, {"s": page(fm, "| Study design | RCT |")}, self.RAW)
        out = run_lint(v)
        assert out["stale"] == 0 and out["hash_untracked"] == 0

    def test_numeric_hash_yaml_int_regression(self, tmp_path):
        # 回歸：全數字雜湊會被 YAML 載成 int；未 str() 轉型會造成 str≠int 恆真 → 假性過期
        data, numeric_hash = find_numeric_hash_content()
        fm = {**FM_BASE, "sources": "[num.pdf]", "source_hash": numeric_hash}  # 不加引號
        v = write_vault(tmp_path, {"s": page(fm, "| Study design | RCT |")},
                        {"num.pdf": data})
        assert run_lint(v)["stale"] == 0

    def test_missing_raw_file_is_skipped(self, tmp_path):
        # raw/ 為空（fresh public clone）→ 不誤判
        fm = {**FM_BASE, "sources": "[ghost.pdf]", "source_hash": "abc123"}
        v = write_vault(tmp_path, {"s": page(fm, "| Study design | RCT |")}, raw={})
        out = run_lint(v)
        assert out["stale"] == 0 and out["hash_untracked"] == 0


# ============================================================
#  Group 3 — EBM 型別分類（端對端）
# ============================================================
class TestEBMClassification:
    def test_study_page_full_check(self, tmp_path):
        body = "| Study design | RCT, randomized |\npico 描述但刻意不補 GRADE/Applicability"
        fm = {**FM_BASE, "sources": "[a.pdf]"}
        out = run_lint(write_vault(tmp_path, {"s": page(fm, body)}, {"a.pdf": b"x"}))
        assert out["source_study"] == 1
        assert out["ebm_missing_study"] >= 1          # 缺 8 欄中的若干 → 真缺口

    def test_guideline_page_light_check(self, tmp_path):
        body = ("| Study design | clinical practice guideline |\n"
                "Applicability 台灣適用。Bottom line：建議使用。")
        fm = {**FM_BASE, "sources": "[g.pdf]"}
        out = run_lint(write_vault(tmp_path, {"s": page(fm, body)}, {"g.pdf": b"x"}))
        assert out["source_guideline"] == 1
        assert out["ebm_missing_guideline"] == 0       # 3 輕量欄齊全

    def test_undetermined_not_silently_downgraded(self, tmp_path):
        # 無 Study design 欄、也無 guideline 線索 → 應列「型別待確認」，非靜默當 guideline
        body = "一段沒有標註研究設計的敘述。"
        fm = {**FM_BASE, "sources": "[m.pdf]"}
        out = run_lint(write_vault(tmp_path, {"s": page(fm, body)}, {"m.pdf": b"x"}))
        assert out["source_undetermined"] == 1
        assert out["ebm_undetermined"] >= 1
        assert out["source_guideline"] == 0            # 關鍵：沒有被吞進 guideline


# ============================================================
#  Group 4 — classify_source / check_stale（純函式單元測試）
# ============================================================
#  重構後 EBM 分類與過期檢查已抽成可 import 的純函式，
#  毋須再起 subprocess —— 直接呼叫、毫秒級、定位精準。
#  Group 2/3 的 subprocess 案例保留為 --json 摘要的 contract test。
def make_page(body, fm=None, name="s"):
    """組出 classify_source / check_stale 需要的最小 page dict。"""
    f = {"type": "source"}
    if fm:
        f.update(fm)
    return {"name": name, "fm": f, "body": body}


class TestClassifySourceUnit:
    def test_non_source_returns_none(self):
        assert wiki_lint.classify_source(make_page("x", {"type": "concept"})) is None

    def test_study_full_missing(self):
        # body 刻意不出現任何 EBM 欄位別名字 → 8 欄應全判為缺
        body = "| Study design | RCT, randomized |\n正文僅描述方法與收案，未填其餘欄位。"
        res = wiki_lint.classify_source(make_page(body))
        assert res["category"] == "study"
        assert set(res["missing"]) >= {"GRADE", "RoB", "Applicability"}

    def test_guideline_light_complete(self):
        body = ("| Study design | clinical practice guideline |\n"
                "Applicability 台灣適用。Bottom line：建議使用。")
        res = wiki_lint.classify_source(make_page(body))
        assert res["category"] == "guideline"
        assert res["missing"] == []

    def test_undetermined_not_downgraded(self):
        res = wiki_lint.classify_source(make_page("沒有標研究設計的敘述。"))
        assert res["category"] == "undetermined"
        assert "缺失" in res["reason"]

    def test_conflict_keyword_undetermined(self):
        # Study design 欄同時命中研究與非研究關鍵字 → 衝突，不靜默選邊
        body = "| Study design | randomized controlled guideline |"
        res = wiki_lint.classify_source(make_page(body))
        assert res["category"] == "undetermined"
        assert "衝突" in res["reason"]

    def test_pico_structured_bold_counts(self):
        # 結構式 **P**/**I**/**C**/**O** 應視為 PICO 存在
        body = "| Study design | RCT |\n| **P** | a | **I** | b | **C** | c | **O** | d |"
        res = wiki_lint.classify_source(make_page(body))
        assert "PICO" not in res["missing"]


class TestCheckStaleUnit:
    def _hash(self, data):
        return hashlib.sha256(data).hexdigest()[:16]

    def test_correct_hash(self, tmp_path):
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.pdf").write_bytes(b"v1")
        page = make_page("x", {"sources": ["a.pdf"], "source_hash": self._hash(b"v1")})
        stale, untracked = wiki_lint.check_stale(page, str(tmp_path / "raw"))
        assert stale == [] and untracked == []

    def test_wrong_hash_stale(self, tmp_path):
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.pdf").write_bytes(b"v1")
        page = make_page("x", {"sources": ["a.pdf"], "source_hash": "deadbeefdeadbeef"})
        stale, untracked = wiki_lint.check_stale(page, str(tmp_path / "raw"))
        assert len(stale) == 1 and stale[0][0] == "a.pdf"

    def test_missing_hash_untracked(self, tmp_path):
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.pdf").write_bytes(b"v1")
        page = make_page("x", {"sources": ["a.pdf"]})
        stale, untracked = wiki_lint.check_stale(page, str(tmp_path / "raw"))
        assert stale == [] and untracked == ["a.pdf"]

    def test_numeric_hash_str_coercion(self, tmp_path):
        # recorded_hash_for 須 str() 轉型，否則 YAML int 與 str 永不相等 → 假性過期
        data, numeric = find_numeric_hash_content()
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "n.pdf").write_bytes(data)
        page = make_page("x", {"sources": ["n.pdf"], "source_hash": int(numeric)})
        stale, _ = wiki_lint.check_stale(page, str(tmp_path / "raw"))
        assert stale == []

    def test_no_sources_skipped(self, tmp_path):
        (tmp_path / "raw").mkdir()
        stale, untracked = wiki_lint.check_stale(make_page("x"), str(tmp_path / "raw"))
        assert stale == [] and untracked == []


class TestRecordedHashForUnit:
    def test_scalar_single_source(self):
        assert wiki_lint.recorded_hash_for("a.pdf", "abc123", 1) == "abc123"

    def test_scalar_ignored_when_multi_source(self):
        # 多來源不可用純量（無法分辨對應哪個檔）→ None
        assert wiki_lint.recorded_hash_for("a.pdf", "abc123", 2) is None

    def test_dict_basename_match(self):
        rec = {"a.pdf": "h1"}
        assert wiki_lint.recorded_hash_for("raw/a.pdf", rec, 2) == "h1"

    def test_numeric_int_coerced_to_str(self):
        assert wiki_lint.recorded_hash_for("a.pdf", 123456, 1) == "123456"


# ============================================================
#  TODO（後續延伸）
# ============================================================
# 1. 補圖譜指標（孤立率/壞鏈率/雙向率）的邊界案例。
# 2. 補 frontmatter YAML 解析失敗（如 updated 後接註解）→ fm_missing 標記的測試。
