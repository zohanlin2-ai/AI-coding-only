# Changelog

本專案的所有重大變更都將記錄在此檔案中。

## [0.1.5] - 2026-04-17

### Added
- **專業級技術圖表**: 引入 AI 生成的高畫質 (HD) 系統架構圖與活動流程圖，大幅提升設計文件的視覺質感與技術可讀性。
- **高清資產部署**: 於 `docs/assets/` 部署 `overview_diagram_pro.png` 與 `activity_diagram_pro.png`。
- **測試文檔**: 建立 `TESTING.md`，提供系統化的自動化測試評估與手動 QA 指引。

## [0.1.0] - 2026-04-17

### Added
- **設計文件**: 建立並優化 `c_ffmpeg_sdl_player.md`，包含系統架構、核心流程與 A/V Sync 邏輯。
- **環境開發包**:
    - 安裝 `mingw-w64-x86_64-ffmpeg` (libavcodec, libavformat, etc.)。
    - 安裝 `mingw-w64-x86_64-SDL2`。
- **建置系統**: 建立 `Makefile`，支援 MinGW-w64 下的自動編譯與連結。
- **Git 配置**: 建立 `.gitignore` 以過濾編譯產物。
- **驗證程式碼**: 在設計文件中加入 `main.c` 驗證用範例碼與 DLL 執行說明。

- **詳細設計**: 補充 `Packet Queue` 與 `Frame Queue` 的同步機制說明。

## [0.1.2] - 2026-04-17

### Added
- **技術細節**: 新增「記憶體管理協議」，詳細說明 AVPacket 與 AVFrame 的生命週期。
- **同步算法**: 加入 A/V Sync 的詳細閾值設定與補償策略說明。
- **故障排除**: 在 README 中新增常見錯誤代碼與開發疑難排解。
- **發展藍圖**: 建立三階段的開發 Roadmap。

### Updated
- **資料結構**: 擴充 `PlayerContext` 為具備執行緒與佇列的 `VideoState` 實戰結構。

## [0.1.3] - 2026-04-17

### Added
- **系統活動圖 (Activity Diagram)**: 新增播放器生命週期流程圖，涵蓋初始化、解碼循環與資源回收。
- **詳細時序圖 (Sequence Diagram)**: 升級時序圖，加入音訊處理流程、平行處理 (parity) 邏輯與同步點說明。

## [0.1.4] - 2026-04-17

### Added
- **靜態圖檔資產**: 完成 Mermaid 代碼至 PNG 圖片的轉換，解決非 Mermaid 環境下的顯示問題。
- **資產目錄**: 建立 `docs/assets/` 用於存放專案相關技術圖表。

### Updated
- **文檔整合**: 在 `c_ffmpeg_sdl_player.md` 中嵌入 PNG 圖片，並保留 Mermaid 原始碼供未來編輯使用。
