# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-05-14
### Added
- **永久記憶勾選狀態**：在「備課管理」中勾選單字後，狀態會儲存至資料庫。即使關閉 App 或離開頁面，勾選狀態也會保留。
- **自選上課邏輯優化**：首頁的「開始上課」現在會自動過濾，僅出現家長在備課管理中「有打勾」且「尚未學會」的單字。
- **上課循環機制**：在上課模式中到達最後一張卡片後，點擊「下一個」會自動循環回到第一張，方便家長帶領寶寶反覆練習。
- **全自動語言偵測系統**：系統會自動根據輸入內容判斷口音。若遇到中日文漢字重疊（如「家族」），提供微型切換鈕供家長手動快速校正。

### Fixed
- **Android 權限修復**：新增 Android 網路權限設定，確保 App 在 Release 正式版模式下也能正常搜尋 Unsplash 圖庫圖片。
- **發音不準修復**：優化語言偵測邏輯，解決日文漢字（如「自転車」）被誤判為中文導致發音錯誤的問題。

### Changed
- **上課介面優化**：將「還要多練習」按鈕更名為更直覺的「下一個」，並更換為箭頭圖示，降低家長心理壓力並提升導覽順暢度。

## [0.2.0] - 2026-05-13
### Added
- **Phase 3**: 開發 `ClassView`（閃卡介面）提供全螢幕沉浸式教學。
- **Phase 3**: 整合 `flutter_tts` 自動朗讀功能，並實作曝光次數紀錄邏輯。
- 支援 Windows 與 Linux 桌面端的 `sqflite` 資料庫配置。

### Changed
- **功能異動**：移除「AI 圖片生成」功能與相關設定頁面。
  - *原因說明*：考量市面上缺乏穩定免費 API，為確保教學流暢，統一回歸使用高品質的 Unsplash 圖庫。

### Fixed
- 升級 `SettingsNotifier` 語法至最新的 `Notifier` 以修復編譯錯誤。

## [0.1.0] - 2026-05-12
### Added
- 專案初始化：設定 `flutter_tts`, `sqflite`, `riverpod`, `http` 等核心依賴。
- **Phase 1 & 2**: 完成 `SettingsView`, `AddPrepView`, `PrepListView` 等基礎管理介面。
- 實作 `ApiService` 與 `DatabaseService` 核心邏輯。
