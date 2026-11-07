# 交接檔（handoff.md）

## ⏯️ 目前做到哪

2026-11-07：門診成績單動畫配音版（民國 115 年 10 月）已上[衛教網站首頁](https://philia81301-commits.github.io/obesity-education-clinic/)。每月更新已併入月報技能第四步之五，數字、旁白、字幕和畫面都讀 `report/data/YYYY_MM.json`。

2026-11-07：健康旅程攻略動畫配音版（4 分 50 秒，`journey/`）也已換上網站首頁左側。醫師看片後改三句：想吐頁「大多數人的副作用會越來越輕，不要擔心」、意志力頁「代表藥有發揮作用」、睡眠「睡 6～7 小時」。改句子流程：`journey/script.py` → `python make_audio.py`（只重做改到的句子）→ `python render.py check` → `python render.py full`（約 12 分鐘）→ 把 `out/journey-guide-phone.mp4` 與封面複製到衛教網站 `design/assets-video/`，改 `GUIDE.ver` 再 build。1080p 候診區版只在家用機 `journey/out/`，尚未換到候診區。

## 🚦 目前狀態

- 10 月版回歸測試：21 句旁白逐字相同，26 張抽樣畫面逐像素相同。
- 用 9 月 stats 測過資料轉換與畫面；8 種錯誤情境都會被擋下。
- **完整流程（含配音、成片）還沒實跑過，11 月月報是第一次。**
- 候診區資料夾 `減重門診衛教影片\候診區輪播_2026_11` 仍是舊版，新版未實測電視。
- 成片、音檔、貼圖都不在 git。1080p 成片只在家用機 `report/out/`，網站上是 720p 版，可重新產生。

## ➡️ 下一步

**醫院電腦第一次開工（只需做一次）：**

```powershell
chezmoi update
claude plugin marketplace update weight-clinic
claude plugin update weight-clinic@weight-clinic
git -C C:\projects\obesity-education-clinic pull
gh repo clone philia81301-commits/video-pilot-boss C:\projects\video-pilot-boss
pip install edge-tts imageio-ffmpeg playwright pillow
```

更新後重開 Claude。在 `report\` 執行 `python monthly.py assets` 準備貼圖；若讀不到，先在 OneDrive 把 `文件\貼圖_20261028` 設為「永遠保留在此裝置」。

**之後：** 11 月月報定稿後，依月報技能第四步之五跑影片。流程與手動填表對照見 `report/README.md`。

## ⏳ 待醫師決定

1. 新版成績單要不要放進候診區（建議先實測電視）。
2. 網站公開的門診統計，院方是否已確認（交接文件記為待確認，新版公開的統計比舊版多）。
3. 健康旅程攻略新版要不要放進候診區；片中肌力訓練每週 2～3 次、進食順序、紅旗「或到急診就醫」三處醫師尚未明確表示意見。

## ⚠️ 注意事項

- **月報資料驅動腳本只在家用機：** `monthly_stats.js` 等五支尚未收進外掛，所以醫院那台沒有 stats JSON，要手動填資料檔。收進外掛前要先做個資掃描，版本升 0.2.0。
- **舊技能 `weight-clinic-scorecard-video`：** 家用機找不到，可能在院內帳號。如果還在，不要用，它會把網站蓋回無聲版。
- **換片要改 `VIDEO.ver`：** 在 `obesity-education-clinic/tools/build-site.js`，不改手機會卡舊片。
- **`edge-tts` 是非官方服務：** 曾出現 403，更新套件後恢復。若再失敗就回報，不要自行改用其他語音。
- **月報技能有兩個來源：** 外掛 repo `weight-clinic-plugin`，以及 chezmoi 的 `.chezmoitemplates/skill-weight-clinic.md`。`~/.claude/skills/` 底下是產生檔，不要直接改。
- **Agent 記憶不跨電腦：** 長期規則寫在 `agents.md`。

## 🕐 最後更新

- 時間：2026-11-07
- 更新者：Claude Code（Opus 5.5）@ DESKTOP-LVSV9Q5（家用機）
- Git push：✅ 已推
- L3 Obsidian：併入 `obesity-education-clinic/專案工作流程.md`
