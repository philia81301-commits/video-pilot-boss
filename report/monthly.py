"""每月成績單影片的前置工作。

python monthly.py stats <stats_YYYY_MM.json> <YYYY_MM>   從月報的 stats JSON 產生 data/YYYY_MM.json
python monthly.py check <YYYY_MM> [上月 YYYY_MM]          檢查句子，輸出給醫師看的對照表
python monthly.py assets                                  從 OneDrive 準備人物貼圖（貼圖不進公開 repo）
"""
import json
import os
import sys
from pathlib import Path

from content import ROOT, blocking_issues, checks, derive, lines, load, show, tx_share

DATA = ROOT / "data"
OUT = ROOT / "out"

GROUPS = {
    "Mounjaro": "glp1", "Ozempic": "glp1", "Wegovy": "glp1", "Rybelsus": "glp1", "Saxenda": "glp1",
    "無藥物": "lifestyle",
    "Contrave": "other_oral", "Xenical": "other_oral", "Jardiance": "other_oral", "Acarbose": "other_oral",
    "併用/轉換": "combo",
    "手術": "surgery",
}
BUDGET_KEYS = {"1000以下": "<1000", "1000~4500": "1000-4500", "4500~8000": "4500-8000", "8000~15000": "8000-15000"}
BAND_KEYS = {"追蹤3-5個月": "3-5", "追蹤6-8個月": "6-8", "追蹤9-11個月": "9-11", "追蹤12個月以上": "12+"}


def from_stats(stats_path, month):
    s = json.loads(Path(stats_path).read_text(encoding="utf-8"))
    if s["ym"].replace("-", "_") != month:
        raise SystemExit(f"stats 的月份是 {s['ym']}，和指定的 {month} 不同")
    year, mon = map(int, month.split("_"))
    q = s["q"]

    groups, unknown = {}, []
    for row in s["drugs"]:
        key = GROUPS.get(row["drug"])
        if key:
            groups[key] = groups.get(key, 0) + row["n"]
        else:
            unknown.append((row["drug"], row["n"]))
    if groups.get("glp1") != s["glp1"]:
        raise SystemExit(f"腸泌素藥物合計 {groups.get('glp1')} 與月報 glp1={s['glp1']} 不符，先確認藥物歸類")
    small = [k for k, n in groups.items() if n < 10]
    for k in small:
        del groups[k]

    diseases = [dict(label=r["label"], n=r["n"], v=round(r["n"] / q["n"] * 100, 2))
                for r in q["disease"] if r["label"] != "無共病"][:5]
    none_row = next(r for r in q["disease"] if r["label"] == "無共病")

    budget = {BUDGET_KEYS[r["label"]]: dict(band=BUDGET_KEYS[r["label"]], n=r["n"], v=r["pct"])
              for r in q["budgetPct"] if r["label"] in BUDGET_KEYS}
    timeline = [dict(band=BAND_KEYS[m["band"]], n=m["n"], v=m["pct"]["mean"]) for m in s["milestone"]]
    m3 = s["milestone"][0]

    data = dict(
        month=month,
        roc_month=f"民國 {year - 1911} 年 {mon} 月",
        period=f"民國 114 年 9 月至 {year - 1911} 年 {mon} 月",
        ht_check=s["htCheck"],
        n=s["n"], age=s["age"]["mean"], bw=s["bw1"]["mean"], bmi=s["bmi1"]["mean"],
        female_pct=round(s["female"] / s["n"] * 100), male_pct=round(s["male"] / s["n"] * 100),
        weight_up_pct=round(q["profile"]["cur"]["weightUpPct"]),
        survey_n=q["n"],
        any_comorbid_pct=round(100 - none_row["n"] / q["n"] * 100, 1),
        diseases=diseases,
        treatments=groups,
        m3=dict(n=m3["n"], pct=m3["pct"]["mean"], success_pct=round(m3["successRate"])),
        timeline=timeline,
        budget=[budget[k] for k in ("<1000", "1000-4500", "4500-8000", "8000-15000")],
    )
    DATA.mkdir(exist_ok=True)
    dest = DATA / f"{month}.json"
    if dest.exists():
        raise SystemExit(f"{dest} 已存在，確認要重做的話請先手動移開")
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("已寫入", dest)
    if unknown:
        print("⚠ 這些藥物沒有歸類，也不會出現在圓餅圖：", unknown)
    if small:
        print("⚠ 這些治療組別 n<10，已從影片移除：", small)


def metrics(D):
    d = derive(D)
    rows = [
        ("累積個案", f"{D['n']} 位"), ("平均年齡", f"{show(D['age'])} 歲"), ("起始體重", f"{show(D['bw'])} 公斤"),
        ("起始 BMI", show(D["bmi"])), ("女性／男性", f"{D['female_pct']}% / {D['male_pct']}%"),
        ("來診前體重上升", f"{D['weight_up_pct']}%"), ("初診問卷", f"{D['survey_n']} 份"),
        ("合併健康問題", f"{D['any_comorbid_pct']}%（每 4 人約 {d['any_k']} 人）"),
    ]
    rows += [(f"疾病第 {i + 1} 名", f"{r['label']} {r['v']:.0f}%（n={r['n']}）") for i, r in enumerate(D["diseases"])]
    names = dict(glp1="腸泌素藥物", lifestyle="生活型態調整", other_oral="其他口服藥物", combo="併用／轉換", surgery="手術評估")
    rows += [(names[k], f"{show(tx_share(n, D['n']))}%（n={n}）") for k, n in D["treatments"].items()]
    rows += [
        ("3–5 個月平均減重", f"{show(D['m3']['pct'])}%（n={D['m3']['n']}）"),
        ("80 公斤換算", f"{show(d['kg80'])} 公斤"), ("減 5% 以上", f"{show(D['m3']['success_pct'])}%"),
    ]
    rows += [(f"追蹤 {r['band']} 個月", f"{show(r['v'])}%（n={r['n']}）") for r in D["timeline"]]
    rows += [(f"預算 {r['band']}", f"{show(r['v'])}%（n={r['n']}）") for r in D["budget"]]
    return rows


def check(month, prev_month=None):
    D = load(month)
    P = load(prev_month) if prev_month else None
    out = [f"# 成績單影片檢查：{D['roc_month']}", ""]
    if P:
        out.append(f"對照月份：{P['roc_month']}")
        out.append("")

    bad = blocking_issues(D)
    resolved = [i for i in checks(D) if i not in bad]
    if bad:
        out += ["## ⛔ 需要先處理", ""]
        out += [f"- {('句子 ' + k + '：') if k else '資料：'}{msg}" for k, msg in bad]
        out.append("")
    else:
        out += ["## ✅ 檢查通過", ""]
    if resolved:
        out += ["醫師已指定句子的項目：", ""] + [f"- {k}：{msg}" for k, msg in resolved] + [""]

    out += ["## 數字", "", "| 項目 | 本月 | 上月 |", "|---|---|---|"]
    prev = dict(metrics(P)) if P else {}
    for name, value in metrics(D):
        old = prev.get(name, "（無）" if P else "—")
        mark = " **（變動）**" if P and old != value else ""
        out.append(f"| {name} | {value}{mark} | {old} |")
    out.append("")

    new_lines = lines(D)
    old_lines = {x["k"]: x for x in lines(P)} if P else {}
    if P:
        changed = [x for x in new_lines if x["say"] != old_lines.get(x["k"], {}).get("say")]
        out += [f"## 旁白變動（{len(changed)} 句）", ""]
        for x in changed:
            out += [f"- 上月：{old_lines.get(x['k'], {}).get('say', '（無）')}", f"- 本月：{x['say']}", ""]
    out += ["## 本月完整旁白", ""] + [f"{i + 1}. {x['say']}" for i, x in enumerate(new_lines)] + [""]

    OUT.mkdir(exist_ok=True)
    dest = OUT / f"check_{month}.md"
    dest.write_text("\n".join(out), encoding="utf-8")
    print("對照表：", dest)
    print("需要先處理：", len(bad))
    for k, msg in bad:
        print(" -", k or "資料", msg)
    return 1 if bad else 0


def assets():
    from PIL import Image

    src = Path(os.environ["USERPROFILE"]) / "OneDrive" / "文件" / "貼圖_20261028"
    dest = ROOT / "assets"
    dest.mkdir(exist_ok=True)
    for name in ("whoop", "bravo"):
        out = dest / f"{name}.png"
        if out.exists():
            print("已存在", out)
            continue
        Image.open(src / f"sticker_{name}_transparent.png").resize((720, 720), Image.LANCZOS).save(out)
        print("已產生", out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["assets"]:
        assets()
    elif len(args) == 3 and args[0] == "stats":
        from_stats(args[1], args[2])
    elif len(args) in (2, 3) and args[0] == "check":
        sys.exit(check(args[1], args[2] if len(args) == 3 else None))
    else:
        raise SystemExit(__doc__)
