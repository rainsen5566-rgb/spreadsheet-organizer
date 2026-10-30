# 後端轉檔獨立測試

此為本機 API 原型，不是已公開的雲端服務。原網站尚未變更。

透過 HTTP POST /convert 接收 XLSX，由 LibreOffice 逐張可見工作表匯出 PDF，
逐張補齊偶數頁後合併回傳。來源內容不寫回原檔、不呼叫 AutoFit、不改列印設定。
暫存副本只變更工作表可見狀態；公式會由 LibreOffice 重新計算，不能保證與 Excel 完全相同。
需要已安裝且有授權使用的字型；Linux 雲端需另行確認標楷體授權及安裝。

啟動：安裝 requirements.txt，設定 SOFFICE_PATH 與 PDF_BACKEND_TOKEN，執行 python server.py。
目前僅綁定 127.0.0.1，不提供 CORS。POST 需 Authorization: Bearer 金鑰及原始 XLSX request body。
單檔上限 25 MB、解壓上限 100 MB、最多 100 張可見工作表。
拒絕巨集、外部連結及外部關聯。作業完成清除暫存檔，不記錄檔案內容。

正式上線前仍需：隔離容器、限制程序資源與對外連線、HTTPS、使用者驗證、
請求與佇列上限、逾時時終止整個程序樹，以及網站後端串接。
不得直接把此測試 HTTPServer 暴露到公網。

## 2026-10-30 實際測試結果

- LibreOffice 26.2.6.3，官方 Windows MSI SHA-256 核對通過。
- HTTP 健康檢查、授權失敗、錯誤檔案拒絕、實際轉檔回傳均通過。
- 使用已提供的兩張單頁工作表：1、1 頁各補成 2 頁，合併 4 頁。
- 58 個非空白儲存格文字全部保留，包含 094628；來源檔案 SHA-256 未改變。
- PDF 嵌入 DFKaiShu-SB-Estd-BF 標楷體，未替換成新細明體。
- 每張工作表擴充為 202 列的測試：分別 6、7 頁，合併補白後共 14 頁。
- PDF 內容頁、補白頁範圍有效，單頁範例皆為 792 × 612 點。
- 已渲染檢視單頁範例及多頁範例的第二張工作表首頁；未用 Adobe 開啟。
- 工作暫存資料夾已清空；未修改公開網站，未部署雲端主機。

此結果只代表上述案例通過，不能保證複雜 Excel 格式與 Microsoft Excel 完全一致。

## 雲端部署準備

提供 Dockerfile、Render Blueprint 與 Gunicorn WSGI adapter。
以本 backend 目錄作為獨立部署根目錄；不要把整個網站資料夾或 runtime 上傳。
render.yaml 預設 free，關閉自動部署；尚未建立任何雲端服務。
容器只包含開源中文字型，尚未包含 Windows 的標楷體，因此雲端字型保留尚待驗證。
不得把本機 Windows 字型直接複製到公開映像；應先確認雲端使用授權。
PDF_BACKEND_TOKEN 只存後端與 Sites 的伺服器端秘密設定，不交給瀏覽器。
現有網站為靜態版本，需增加同源伺服器端代理才能安全串接。
此部署設定尚未經 Docker 建置與雲端測試，不等於正式上線版本。
