# 試算表整理小工具

提供試算表轉檔、Excel 多工作表合併與 PDF 匯出、依欄位分類拆檔。

## 下載與使用

請到本儲存庫的 [Releases](https://github.com/rainsen5566-rgb/spreadsheet-organizer/releases) 頁面下載已正式發布的使用者套件。

第一次使用請下載 `SpreadsheetOrganizer_v版本號.zip`，解壓到桌面或個人資料夾，執行 `SpreadsheetOrganizer.exe`。亦可直接下載 Release 附件中的 `SpreadsheetOrganizer.exe`。

- 上方拖入檔案後立即處理。
- 下方可一次加入多檔或分次追加，按「轉檔」後開始。
- Excel 匯出 PDF 與自動調整欄列需要桌面版 Microsoft Excel。

## 程式內更新

從 v1.8 起支援檢查更新。程式啟動時在背景檢查，也可點選「檢查更新」。有新版時顯示更新內容，使用者同意後才下載及安裝。

更新會核對 GitHub Release 提供的 SHA-256、保留上一版備份，並在新版啟動失敗時恢復原版。程式資料夾需可寫入，網路無法連線時仍可使用原有功能。啟動檢查每台電腦最多每六小時一次，手動檢查不受這個間隔限制。

更新僅取得版本資訊及下載程式，不會上傳匯入檔案或工作資料。

## 維護者發布方式

每次發布使用遞增的正式版本標籤，例如 `v1.8`、`v1.9`、`v1.10`。在 Release 附加檔名固定的 `SpreadsheetOrganizer.exe` 和對應的使用者版 ZIP，再發布為正式最新版；不要勾選 Pre-release。程式會依版本號判斷更新。

公開套件只包含執行檔及使用說明，維護用原始碼另外保存。GitHub 自動產生的 Source code 附件是本儲存庫的文件快照，不是可執行程式。
