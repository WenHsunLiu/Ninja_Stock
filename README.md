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
填入您的 Supabase URL 與 API Key。

### 2. 本機開發環境
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 驗證資料庫連線
```bash
python3 scripts/verify_connection.py
```

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
