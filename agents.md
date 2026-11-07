# video-pilot-boss（專案藍圖）

> 任何 Agent 開工先讀本檔與 `handoff.md`。

## 專案簡介

減重門診衛教影片的動畫版。用瀏覽器逐格截圖加程式合成，不需要影片剪輯軟體。對象是候診民眾與考慮加入門診的人。

## 路線圖

- [x] 停滯期魔王關試作（25 秒，根目錄），醫師認可聲音、效果與文字
- [x] 門診成績單動畫版（1 分 43 秒，`report/`），已上衛教網站首頁
- [x] 成績單改為每月資料驅動，併入月報技能「減重門診成效分析」第四步之五
- [ ] 11 月月報時第一次實跑完整流程
- [ ] 候診區電視實測，決定是否換掉候診區舊版
- [x] 健康旅程攻略動畫配音版（4 分 50 秒，`journey/`），2026-11-07 上衛教網站首頁

## 資料夾結構

```
video-pilot-boss/
├── agents.md、handoff.md
├── README.md
├── index.html、make_audio.py、render.py、cut_mascot.py、timing.json   # 魔王關片
├── journey/                # 健康旅程攻略動畫版：script.py 改句子 → make_audio.py → render.py full
└── report/                 # 門診成績單，每月流程見 report/README.md
    ├── data/YYYY_MM.json   # 每月資料（匿名彙總）
    ├── content.py          # 旁白、字幕與句子檢查
    ├── monthly.py          # 轉資料、對照表、準備貼圖
    ├── make_audio.py、render.py、index.html、timing.json
    └── assets/、audio/、out/   # 不進 git
```

## 工作約定

- 所有回應與文件用繁體中文。公開 repo，只放匿名彙總，不放個案資料與人物貼圖。
- 語音固定 `zh-TW-HsiaoChenNeural`，句中不換人聲。
- 影片裡不唸 GLP-1：泛指針劑時說「腸泌素針劑」。成績單 43% 那組含口服 Rybelsus，所以說「腸泌素藥物」。
- BMI 只放畫面、不唸。AI 語音不自稱醫師本人。候診區影片要保留字幕（可能靜音播放）。
- 考慮手術 n=8 不呈現；n<10 不得當亮點。
- 模組衛教短片仍維持醫師本人錄音，合成語音只用於動畫版。
- 對外發布（上網站、候診區、公開 repo 改動）先問醫師。

## 同步層級

| 層級 | 位置 |
|---|---|
| L1 本地 | `C:\projects\video-pilot-boss`，`agents.md`＋`handoff.md` |
| L2 GitHub | `philia81301-commits/video-pilot-boss`（公開） |
| L3 Obsidian | 併入 `2ndBrain/obesity-education-clinic/專案工作流程.md` |
