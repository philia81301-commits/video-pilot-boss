# 衛教影片動畫試作

用瀏覽器逐格截圖合成影片，不需要影片剪輯軟體。動畫以 HTML 手寫，旁白用 `edge-tts` 的台灣腔語音 `zh-TW-HsiaoChenNeural`。

| 內容 | 位置 |
|---|---|
| 停滯期魔王關（25 秒） | 根目錄 |
| 減重門診成績單，每月更新（1 分 43 秒） | `report/` |

## 需要的環境

- Python，安裝 `edge-tts`、`imageio-ffmpeg`、`playwright`、`pillow`
- Microsoft Edge

## 製作方式

在對應資料夾執行：

```bash
python make_audio.py
python render.py full
```

魔王關片要先執行一次 `python cut_mascot.py`。`render.py` 也可以只輸出指定秒數的畫面來檢查版面，例如 `python render.py snap 1.5 4.2`。

## 不在此 repo 的檔案

影片、音檔和人物貼圖都沒有上傳。`report/` 製作前要自備 `report/assets/whoop.png` 和 `report/assets/bravo.png`。

## 資料與使用限制

- 成績單的數字是門診匿名彙總統計，不含個案資料。
- 成績單的數字每月更新，每月資料在 `report/data/`，流程見 `report/README.md`。
- 內容僅供衛教，實際治療以醫師評估為準。
