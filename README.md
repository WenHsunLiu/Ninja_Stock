# Ninja_Stock 🥷📈

Ninja_Stock 是一個專為股票數據追蹤、分析與自動化設計的專案。

## 雲端架構與跨裝置支援
- **版本控制與同步**：GitHub Private Repository
- **雲端開發環境**：支援 GitHub Codespaces（一鍵在瀏覽器或各裝置直接開箱即用開發）
- **雲端資料庫**：Supabase (PostgreSQL)，確保所有裝置讀取同一套資料源

## 快速開始

### 1. 複製環境變數範本
```bash
cp .env.example .env
```
在本機 `.env` 填入開發用的 Supabase URL 與 publishable key，也可用未追蹤的
`.streamlit/secrets.toml`。正式服務使用各執行環境的私密設定
（Streamlit Secrets 或 GitHub Actions Secrets）。操作手冊、共享文件、
截圖及版控一律只用預留值。受控的本機憑證檔應限制為僅帳號擁有者可讀寫。

### 2. 本機開發環境
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 驗證行情排程連線
```bash
python3 scripts/verify_connection.py
```

## 帳本與行情排程權限

- Streamlit 使用 `SUPABASE_URL` 及 `SUPABASE_PUBLISHABLE_KEY`。在網站登入表單輸入預先建立的擁有者帳號及密碼。
- 行情同步使用另一個 Supabase Auth 帳號。排程可讀寫行情、寫入同步紀錄及取得自選股代號。自選股備註、目標價及私人帳本均由擁有者存取。
- Supabase Auth 關閉自行註冊及匿名登入。由管理者建好擁有者及行情帳號，取得兩個帳號各自的使用者 UUID。
- 隔離環境先依序套用 001–004，然後在 SQL Editor 用管理者身分登記這兩個 UUID。請將下列占位符換為角色對應的 UUID。

```sql
INSERT INTO ninja_stock_private.account_roles (user_id, access_role)
VALUES ('<擁有者 UUID>', 'owner'), ('<行情帳號 UUID>', 'market_sync');
```

- 在隔離環境執行 `supabase/tests/application_access.sql`，再驗證擁有者的網頁登入、登出、既有帳本讀寫和行情帳號的同步。正式切換前先備妥兩邊的私密設定、核對可還原備份及備份後的資料變更。004 提交時會收回既有高權限金鑰的應用表存取。安排維護窗口協調套用 SQL、登記帳號及部署程式。

## 數據同步與自動化排程

### 手動 / 批次資料同步 (`scripts/sync_data.py`)
```bash
# 1. 僅同步台股上市上櫃股票清單
python3 scripts/sync_data.py --action stocks

# 2. 同步預設核心股票 (0050, 2330, 2317 等) 最近 5 天行情與三大法人、融資券
python3 scripts/sync_data.py --action bundle --source core --days 5

# 3. 同步自選股清單 (watchlist) 最近 10 天數據
python3 scripts/sync_data.py --action bundle --source watchlist --days 10

# 4. 同步指定個股特定日期區間
python3 scripts/sync_data.py --action bundle --stocks 2330,2454,0050 --start-date 2026-11-01 --end-date 2026-11-09

# 5. 一鍵完整同步 (更新股票清單 + 核心指標股數據)
python3 scripts/sync_data.py --action all
```

### 每日盤後自動化排程 (`scripts/daily_schedule.py`)
台股每日收盤後（建議於 17:30 之後），自動同步當日日K線、三大法人買賣超與融資融券數據：
```bash
# 立即執行一次今日盤後同步 (手動觸發)
python3 scripts/daily_schedule.py --now

# 啟動常駐排程監聽，每日 17:30 自動執行
python3 scripts/daily_schedule.py --time 17:30
```

## 雲端全自動化排程 (GitHub Actions)
即使本機電腦休眠或關機，專案已配置 GitHub Actions 雲端工作流：
- **觸發時機**：每週一至週五台灣時間 17:30 (UTC 09:30) 自動執行。
- **手動觸發**：在 GitHub 倉庫的 `Actions` 分頁中，選擇 `Daily Stock Data Sync` 即可手動一鍵執行。
- **必要環境變數 (GitHub Secrets)**：
  - `SUPABASE_URL`
  - `SUPABASE_PUBLISHABLE_KEY`
  - `SUPABASE_SYNC_EMAIL`
  - `SUPABASE_SYNC_PASSWORD`
  - `FINMIND_API_TOKEN`
