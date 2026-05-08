# C + FFmpeg + SDL2 Video Player

這是一個基於 C 語言、FFmpeg 與 SDL2 實作的跨平台影音播放器專案。本專案目前專注於底層解碼流程與 A/V Sync 的實作。

## 🚀 快速開始

### 1. 安裝環境
請確保您的系統已安裝 **MSYS2** 且配置好 **MinGW-w64** 執行緒環境。詳細步驟請參考 [環境配置指南](c_ffmpeg_sdl_player.md#2-環境配置-windows--mingw-w64)。

### 2. 編譯專案
專案已內建 Makefile，可直接於終端機執行：
```bash
make
```
編譯後的執行檔將產出於 `bin/player.exe`。

### 3. 加入原始碼
- 📝 **[設計文件 (Design Document)](c_ffmpeg_sdl_player.md)**: 包含核心系統架構、執行緒設計、A/V Sync 邏輯（含 **Pro 高清圖表**）。
- 🧪 **[測試驗證指南 (Testing Guide)](TESTING.md)**: 包含自動化測試評估與手動 QA 核取清單。
- 📜 **[變更紀錄 (Changelog)](CHANGELOG.md)**: 完整的版本紀錄與開發進度。

---

## 🛠️ 技術棧與依賴

- **語言**: C99 / C11
- **編譯器**: GCC (MinGW-w64)
- **影音解碼**: [FFmpeg](https://ffmpeg.org/) (libavformat, libavcodec, libswscale)
- **多媒體顯示**: [SDL2](https://www.libsdl.org/)

## 🧬 專案目錄結構

```text
c_player/
├── bin/            # 編譯產出與執行環境
├── src/            # 原始碼存放處
├── Makefile        # 自動化編譯腳本
└── README.md       # 本文件
```

---

## 🛡️ 目前狀態

- [x] 環境工具鏈配置成功 (MinGW-w64)
- [x] 核心函式庫部署成功 (FFmpeg, SDL2)
- [x] 建置系統完成 (Makefile)
- [x] 專業級高清技術圖表優化 (Pro Diagrams)
- [x] 播放器測試驗證指南完成 (TESTING.md)
- [/] 核心播放邏輯實作 (開發中 - 已建立基礎架構)

---

## 🛠️ 故障排除 (Troubleshooting)

| 問題 | 可能原因 | 解決方法 |
| :--- | :--- | :--- |
| **找不到 DLL** | 執行檔目錄缺少依賴 | 從 `C:\msys64\mingw64\bin` 複製必要的 DLL。 |
| **Invalid data (Exit -10949...)** | 影音格式不支援 | 確認檔案路徑正確，或使用 `ffprobe` 檢查格式。 |
| **音畫不同步** | 影像解碼速度過慢 | 開發硬體加速 (HW Decode) 功能或檢查 A/V Sync 邏輯。 |

---

## 🗺️ 開發藍圖 (Roadmap)

### 第一階段：核心引擎 (進行中)
- [x] 環境工具鏈配置 (MinGW-w64 + Makefile)
- [x] FFmpeg/SDL2 庫連結驗證
- [ ] 基礎 Demuxer 與 Video 解碼實作
- [ ] 基礎音訊播放器

### 第二階段：功能補強
- [ ] A/V Sync 音畫同步機制
- [ ] 字幕渲染支援 (libass)
- [ ] 播放控制介面 (GUI)

### 第三階段：專案優化
- [ ] 硬體加速解碼 (VAAPI/DXVA2)
- [ ] 網路串流支援 (RTSP/HLS)
