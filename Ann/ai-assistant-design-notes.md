# AI 助理雛形設計筆記

> 討論日期：2026-05-26

---

## 一、語言選擇

### 推薦：Python

對於 AI 助理 + 自我更新機制，Python 是最佳選擇：

- AI/LLM 生態系最完整（LangChain、Anthropic SDK、OpenAI SDK 等）
- 動態載入模組極為方便（`importlib`），適合熱更新
- subprocess / git 操作簡單
- 測試框架成熟（pytest）
- 跨平台，部署彈性大

### 其他選項比較

| 語言 | 優點 | 缺點 |
|------|------|------|
| **Node.js** | 非同步強、前端整合佳 | AI 生態不如 Python |
| **Go** | 編譯快、部署簡單 | 動態載入模組複雜 |
| **Rust** | 效能極佳 | 開發速度慢，AI 生態弱 |

---

## 二、自我更新機制設計（本機環境）

### 核心挑戰

Python 程式無法直接替換自己正在執行的檔案，需要採用 **Launcher + Core 分離**架構：

```
launcher.py   ← 永遠不更新，只負責啟動與監控
    └── assistant.py  ← 這部分可以被更新、重啟
```

### 更新流程

```
1. assistant 偵測到新版本
2. 通知 launcher「準備更新」
3. launcher 下載、測試新版
4. launcher 殺掉舊 assistant
5. launcher 用新版重新啟動
6. 失敗則 rollback 舊版
```

### 本機特有問題與解法

| 問題 | 解法 |
|------|------|
| 程式執行中無法覆蓋自身 | Launcher 架構分離 |
| 相依套件更新（pip） | virtualenv 隔離，新版用新 venv 測試 |
| 使用者正在對話中被打斷 | 更新排程在對話空檔，或詢問使用者 |
| 沒有網路 / GitHub 連不到 | Graceful fallback，繼續用舊版 |
| 測試環境與執行環境不同 | 同一台機器用 subprocess 隔離跑測試 |

---

## 三、推薦目錄結構

```
~/.ai-assistant/
├── launcher.py          # 核心啟動器，極少更新
├── current/             # 目前執行版本
│   ├── assistant.py
│   ├── plugins/
│   └── requirements.txt
├── staging/             # 下載新版後先放這裡測試
├── versions/            # 保留舊版本（rollback 用）
│   ├── v1.0.2/
│   └── v1.0.1/
├── config.yml           # 使用者設定，永遠不被更新覆蓋
└── logs/
```

---

## 四、GitHub API 更新機制

### 可用的 API

**比對版本：**
```
GET https://api.github.com/repos/{owner}/{repo}/releases/latest
```
回傳 `tag_name`，與本地 `version.txt` 比對即可判斷是否需要更新。

**下載 Source Code：**
```
GET https://api.github.com/repos/{owner}/{repo}/zipball/{tag}
```
用 `requests` 或內建 `urllib` 直接下載 zip，解壓縮到 `staging/`。

**驗證完整性：**
```
GET https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{tag}
```
比對 commit SHA，確認下載內容正確。

### 完整更新流程（純 API，不需要 git 指令）

```
1. GET /releases/latest       → 取得最新 tag
2. 比對本地 version.txt       → 需要更新嗎？
3. GET /zipball/{tag}         → 下載 zip
4. 驗證 SHA                   → 確認完整性
5. 解壓縮到 staging/          → 準備測試
6. 跑 pytest（subprocess）    → 通過才 swap
7. atomic swap → current/     → 重啟 assistant
8. 失敗 → 清除 staging        → 通知使用者
```

### Token 需求

| 情境 | 是否需要 Token |
|------|--------------|
| Public repo，只讀 | ❌ 不需要 |
| Private repo | ✅ 需要 Personal Access Token |
| 避免 rate limit（每小時 60 次） | ✅ 建議加，可提升到 5000 次/小時 |

---

## 五、使用者體驗設計

本機助理可直接與使用者互動確認更新：

```
助理：「偵測到新版本 v1.2.0，包含以下更新：
      - 新增記憶功能
      - 修正回應速度
      現在更新嗎？(yes / 稍後 / 跳過此版本)」
```

---

## 六、版本管理策略

- 用 **git tag** 標記穩定版本，只從 tag 更新而非直接拉 main branch
- 保留最近 N 個版本供 rollback
- 驗證 GitHub commit signature（避免惡意注入）
- 測試在隔離環境（subprocess / virtualenv）執行

---

## 七、建議實作順序

1. **Launcher** — 最簡單，但最關鍵
2. **GitHub 版本偵測** — 用 GitHub API 比對 tag
3. **測試 + swap 機制** — 確保安全更新
4. **AI 對話核心** — 最後加入

每一步都可獨立驗證，避免一開始陷入過高複雜度。
