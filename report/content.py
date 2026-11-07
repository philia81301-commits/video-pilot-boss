"""門診成績單的共用內容：讀每月資料檔、產生旁白與字幕、檢查句子是否仍成立。"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"

DIGITS = "零一二三四五六七八九"
TX_META = [
    ("glp1", "腸泌素藥物", "#2fd2c2"),
    ("lifestyle", "生活型態調整<small>（不用藥）</small>", "#5ee27f"),
    ("other_oral", "其他口服藥物", "#f6b73c"),
    ("combo", "藥物併用／轉換", "#b47ae8"),
    ("surgery", "減重手術評估", "#ff7a9e"),
]
DISEASE_NAMES = {
    "糖尿病/前期": ("糖尿病或糖尿病前期", "糖尿病或前期", "糖尿病／前期"),
}
BUDGET_LABELS = {
    "<1000": "1,000 元以下",
    "1000-4500": "1,000–4,500 元",
    "4500-8000": "4,500–8,000 元",
    "8000-15000": "8,000–15,000 元",
}
BAND_LABELS = {"3-5": "3–5 個月", "6-8": "6–8 個月", "9-11": "9–11 個月", "12+": "12 個月以上"}
FRACTION_WORDS = {1: "一", 2: "兩", 3: "三", 4: "四"}


def available_months():
    return sorted(p.stem for p in DATA.glob("20*_*.json"))


def latest_month():
    months = available_months()
    if not months:
        raise SystemExit("data 資料夾裡沒有每月資料檔")
    return months[-1]


def load(month=None):
    month = month or latest_month()
    path = DATA / f"{month}.json"
    if not path.exists():
        raise SystemExit(f"找不到 {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def zh_int(n):
    """把 0 到 99,999 的整數轉成中文，例如 883 → 八百八十三。"""
    n = int(n)
    if n == 0:
        return DIGITS[0]
    parts, zero = [], False
    for unit, name in ((10000, "萬"), (1000, "千"), (100, "百"), (10, "十"), (1, "")):
        d = n // unit
        n %= unit
        if d:
            if zero and parts:
                parts.append(DIGITS[0])
            zero = False
            parts.append(DIGITS[d] + name)
        elif parts:
            zero = True
    out = "".join(parts)
    return out[1:] if out.startswith("一十") else out


def zh_num(v):
    """42.7 → 四十二點七；8.0 → 八。"""
    text = f"{v:.1f}"
    whole, dec = text.split(".")
    return zh_int(whole) if dec == "0" else zh_int(whole) + "點" + DIGITS[int(dec)]


def show(v):
    text = f"{v:.1f}"
    return text[:-2] if text.endswith(".0") else text


def round_half_up(v, digits=0):
    k = 10 ** digits
    return math.floor(v * k + 0.5) / k


def tx_share(n, total):
    """10% 以上取整數，以下留一位小數。"""
    p = n / total * 100
    return round_half_up(p) if p >= 10 else round_half_up(p, 1)


def half_phrase(p):
    if 43 <= p < 50:
        return "將近一半"
    if 50 <= p <= 53:
        return "一半"
    if 53 < p <= 58:
        return "超過一半"
    return None


def cheng(p):
    """把百分比往下取到 5%，轉成「三成五」這種說法。"""
    base = int(p // 5 * 5)
    tens, ones = base // 10, base % 10
    word = {2: "兩"}.get(tens, DIGITS[tens]) + "成" + ("五" if ones else "")
    return ("超過" if p - base >= 0.05 else "約") + word


def disease_names(label):
    return DISEASE_NAMES.get(label, (label, label, label))


def derive(D):
    """算出畫面與旁白都會用到的衍生值，例如「以 80 公斤為例」。"""
    any_pct = D["any_comorbid_pct"]
    k = int(round_half_up(any_pct / 25))
    kg80 = round_half_up(80 * D["m3"]["pct"] / 100, 1)
    half = D["timeline"][1:]
    low = round_half_up(min(x["v"] for x in half))
    high = round_half_up(max(x["v"] for x in half))
    return dict(any_k=k, kg80=kg80, tr_low=low, tr_high=high)


def checks(D):
    """回傳 (句子代號, 問題)。代號為 None 表示不能靠改句子解決，要先修資料。"""
    issues = []
    ht = D.get("ht_check") or {}
    if not ht:
        issues.append((None, "缺性別身高驗證值 ht_check"))
    elif not (ht["M"] > 170 and ht["F"] < 165):
        issues.append((None, f"性別身高驗證不通過（女 {ht['F']}、男 {ht['M']}），可能性別編碼反轉"))
    if abs(D["female_pct"] + D["male_pct"] - 100) > 1:
        issues.append((None, "女性與男性比例加總不是 100%"))

    for r in D["diseases"]:
        if r["n"] < 10:
            issues.append((None, f"疾病 {r['label']} n={r['n']}，n<10 不得上片"))
    for key, n in D["treatments"].items():
        if n < 10:
            issues.append((None, f"治療組別 {key} n={n}，n<10 不得上片"))
    for r in D["timeline"]:
        if r["n"] < 10:
            issues.append((None, f"追蹤 {r['band']} 個月 n={r['n']}，n<10 不得上片"))
    for r in D["budget"]:
        if r["n"] < 10:
            issues.append((None, f"預算 {r['band']} n={r['n']}，n<10 不得上片"))
    if D["m3"]["n"] < 10:
        issues.append((None, f"3–5 個月成效 n={D['m3']['n']}，n<10 不得上片"))

    values = [r["v"] for r in D["diseases"]]
    if values != sorted(values, reverse=True):
        issues.append(("dis1", "疾病比例沒有由高到低排列，「第一名」可能不正確"))
    if not all(27 <= r["v"] <= 35 for r in D["diseases"][1:4]):
        issues.append(("dis2", "第 2 到 4 名不全在 27–35%，「都在三成上下」不成立"))
    if abs(D["any_comorbid_pct"] - derive(D)["any_k"] * 25) > 3:
        issues.append(("dis3", f"合併比例 {D['any_comorbid_pct']}%，不接近「每四人有幾人」的說法"))
    if half_phrase(D["m3"]["success_pct"]) is None:
        issues.append(("eff3", f"成功率 {D['m3']['success_pct']}%，不適合用「一半」這類說法"))

    top = D["budget"][-1]
    if top["v"] != max(r["v"] for r in D["budget"]):
        issues.append(("bud1", "8,000–15,000 元已不是最多人選的預算"))
    if half_phrase(top["v"]) is None:
        issues.append(("bud1", f"8,000–15,000 元占 {top['v']}%，不適合用「將近一半」這類說法"))

    # 畫面容量：超過就會壓到旁邊的元素，要先調整版面
    if values and max(values) > 48:
        issues.append((None, "疾病比例超過 48%，長條圖會超出版面"))
    if max(r["v"] for r in D["timeline"]) > 13:
        issues.append((None, "追蹤成效超過 13%，柱狀圖會超出版面"))
    if max(r["v"] for r in D["budget"]) > 62:
        issues.append((None, "預算比例超過 62%，長條圖會超出版面"))
    return issues


def lines(D):
    """產生旁白與字幕。say＝唸的文字；sub＝字幕（省略則用 say）；new＝新場景。"""
    d = derive(D)
    dis = D["diseases"]
    total = D["n"]
    glp1 = tx_share(D["treatments"]["glp1"], total)
    life = tx_share(D["treatments"]["lifestyle"], total)
    m3 = D["m3"]
    top_say, top_sub, _ = disease_names(dis[0]["label"])
    top_cheng = cheng(dis[0]["v"])
    mids = "、".join(disease_names(r["label"])[0] for r in dis[1:4])
    k_word = FRACTION_WORDS.get(d["any_k"], zh_int(d["any_k"]))
    eff_phrase = half_phrase(m3["success_pct"]) or f"百分之{zh_num(m3['success_pct'])}"
    bud_phrase = half_phrase(D["budget"][-1]["v"]) or f"百分之{zh_num(D['budget'][-1]['v'])}"
    low, high = d["tr_low"], d["tr_high"]
    tr_say = f"百分之{zh_num(low)}到{zh_num(high)}" if low != high else f"百分之{zh_num(low)}"
    tr_sub = f"{show(low)}% 到 {show(high)}%" if low != high else f"{show(low)}%"

    rows = [
        dict(k="intro1", say="大家好，這裡是高雄榮總家醫部減重門診。"),
        dict(k="intro2", say="帶你看看，門診夥伴的真實數據。"),
        dict(k="ppl1", new=1, say=f"目前累積追蹤{zh_int(total)}位個案，", sub=f"目前累積追蹤 {total} 位個案"),
        dict(k="ppl2", say=f"平均{zh_num(D['age'])}歲，起始體重平均{zh_num(D['bw'])}公斤。",
             sub=f"平均 {show(D['age'])} 歲，起始體重平均 {show(D['bw'])} 公斤"),
        dict(k="ppl3", say=f"來診前半年，百分之{zh_num(D['weight_up_pct'])}的人，體重正在上升。",
             sub=f"來診前半年，{show(D['weight_up_pct'])}% 的人體重正在上升"),
        dict(k="ppl4", say="你不孤單，來看診的人，大多和你一樣正在努力。"),
        dict(k="dis1", new=1, say=f"常合併的健康問題，第一名是{top_say}，{top_cheng}。",
             sub=f"常合併的健康問題，第一名是{top_sub}，{top_cheng}"),
        dict(k="dis2", say=f"{mids}，也都在三成上下。"),
        dict(k="dis3", say=f"大約每四個人，就有{k_word}個人合併至少一種健康問題。"),
        dict(k="dis4", say="好消息是，體重下降，這些問題也常跟著改善。"),
        dict(k="tx1", new=1, say=f"治療方式呢？腸泌素藥物佔百分之{zh_num(glp1)}，生活型態調整不用藥，佔百分之{zh_num(life)}。",
             sub=f"腸泌素藥物 {show(glp1)}%，生活型態調整（不用藥）{show(life)}%"),
        dict(k="tx2", say="用不用藥、用哪一種，都由醫師依你的身體狀況一起討論。"),
        dict(k="eff1", new=1, say=f"追蹤三到五個月，平均體重下降百分之{zh_num(m3['pct'])}。",
             sub=f"追蹤 3 到 5 個月，平均體重下降 {show(m3['pct'])}%"),
        dict(k="eff2", say=f"以八十公斤為例，大約減{zh_num(d['kg80'])}公斤。", sub=f"以 80 公斤為例，大約減 {show(d['kg80'])} 公斤"),
        dict(k="eff3", say=f"有{eff_phrase}的人，減掉百分之五以上的體重，這是醫學上有意義的改善。",
             sub=f"{eff_phrase}的人（{show(m3['success_pct'])}%）減掉 5% 以上體重，這是醫學上有意義的改善"),
        dict(k="tr1", new=1, say=f"追蹤半年以上的人，平均減重大約{tr_say}。", sub=f"追蹤半年以上的人，平均減重大約 {tr_sub}"),
        dict(k="tr2", say="穩穩減、持續回診，比一次減很多更重要。"),
        dict(k="bud1", new=1, say=f"初診問卷裡，{bud_phrase}的人，可以接受每月八千到一萬五千元。",
             sub=f"{bud_phrase}的人，可接受每月 8,000 到 15,000 元"),
        dict(k="bud2", say="看診時可以依你的預算，和醫師一起規劃方案。"),
        dict(k="end1", new=1, say="減重，我們陪你一起走。"),
        dict(k="end2", say="個人成效因人而異，實際治療以醫師評估為準。"),
    ]
    # 句子不再成立時，由醫師在資料檔 overrides 指定新句子
    for row in rows:
        fix = D.get("overrides", {}).get(row["k"])
        if fix:
            row["say"] = fix["say"]
            row["sub"] = fix.get("sub", fix["say"].rstrip("，。？"))
    return rows


def blocking_issues(D):
    """沒有解決的問題：資料問題一律擋下；句子問題要有 overrides 才放行。"""
    fixed = D.get("overrides", {})
    return [(k, msg) for k, msg in checks(D) if k is None or k not in fixed]


def page_data(D):
    """給動畫頁面的資料（render.py 注入成 window.DATA）。"""
    d = derive(D)
    return dict(
        roc_month=D["roc_month"], period=D["period"], n=D["n"], age=D["age"], bw=D["bw"], bmi=D["bmi"],
        female_pct=D["female_pct"], male_pct=D["male_pct"], weight_up_pct=D["weight_up_pct"], survey_n=D["survey_n"],
        any_k=d["any_k"], kg80=d["kg80"], m3=D["m3"],
        diseases=[dict(l=disease_names(r["label"])[2], v=r["v"]) for r in D["diseases"]],
        treatments=[dict(l=label, c=color, n=D["treatments"][key], p=show(tx_share(D["treatments"][key], D["n"])) + "%")
                    for key, label, color in TX_META if key in D["treatments"]],
        timeline=[dict(l=BAND_LABELS[r["band"]], s=f"n={r['n']}", v=r["v"]) for r in D["timeline"]],
        budget=[dict(l=BUDGET_LABELS[r["band"]], v=r["v"]) for r in D["budget"]],
    )
