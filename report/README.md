# 門診成績單動畫影片：每月更新

每月跟著減重門診月報做，月報定稿後才開始。月報若出修正版，影片也要重做。

## 流程

在 `report/` 資料夾執行。

```bash
python monthly.py assets
python monthly.py stats <stats_YYYY_MM.json> YYYY_MM
python monthly.py check YYYY_MM <上月YYYY_MM>
python make_audio.py YYYY_MM
python render.py snap 2.5 12 28 44 56 68 88 100
python render.py full
```

1. `assets`：貼圖不在公開 repo，從 OneDrive 準備。
2. `stats`：把月報的 `stats_YYYY_MM.json` 轉成 `data/YYYY_MM.json`。沒有 stats 檔的電腦，就複製上月資料檔，對照月報手動填。
3. `check`：產生 `out/check_YYYY_MM.md`，列出數字變動、旁白變動和需要處理的問題。**交給醫師確認後才往下做。**
4. `make_audio.py`：有未處理的問題就不會產生配音。
5. `render.py snap`：檢查各幕版面。
6. `render.py full`：約 6 分鐘，輸出 `out/report-YYYY_MM.mp4`、`-phone.mp4` 和 `-poster.jpg`。

## 檢查會擋下的情況

| 問題 | 處理方式 |
|---|---|
| 性別身高驗證不通過 | 先查月報資料 |
| 任何上片組別 n < 10 | 先修資料，不得上片 |
| 數值超出圖表版面 | 先調整版面 |
| 第一名改變、不再「三成上下」、不接近「每四人幾人」、不適合說「一半」、8,000–15,000 元不再最多 | 醫師決定新句子，寫進資料檔 `overrides` |

`overrides` 寫法：

```json
"overrides": { "dis3": { "say": "唸的文字。", "sub": "字幕文字" } }
```

## 手動填資料檔的對照

| 欄位 | 月報來源 |
|---|---|
| `n`、`age`、`bw`、`bmi`、`female_pct`、`male_pct`、`ht_check` | 個案追蹤檔總覽與性別身高驗證 |
| `weight_up_pct`、`survey_n` | 問卷體重變化、有效問卷數 |
| `any_comorbid_pct` | 100 減去「無共病」比例 |
| `diseases` | 不含「無共病」的前五名，由高到低 |
| `treatments` | `glp1`＝Mounjaro＋Ozempic＋Wegovy＋Rybelsus＋Saxenda；`lifestyle`＝無藥物；`other_oral`＝Contrave＋Xenical＋Jardiance＋Acarbose；`combo`＝併用／轉換；`surgery`＝手術 |
| `m3`、`timeline` | 追蹤區間的人數、平均減重%、成功率 |
| `budget` | 問卷費用分布，四個金額區間，不含考慮手術 |

## 內容原則

- 不出現處方藥商品名。`glp1` 組含口服 Rybelsus，所以叫「腸泌素藥物」，不叫針劑。
- 預算只能說「可接受的每月預算」，不是實際花費。
- 追蹤區間是不同個案，畫面要註明不是同一群人。
- AI 語音不自稱醫師本人；語音固定 `zh-TW-HsiaoChenNeural`，句中不換人聲。
- 結尾保留資料來源與「個人成效因人而異，實際治療以醫師評估為準」。
