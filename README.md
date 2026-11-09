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
