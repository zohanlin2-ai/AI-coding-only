# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-05-14
### Changed
- **Documentation Internationalization**: Translated all project documentation (`README.md`, `CHANGELOG.md`) from Chinese to English to improve accessibility for a global audience.
- **Source Code Comments**: Converted all Chinese comments within the `lib/` directory to English.
- **UI Labels**: Standardized language labels (e.g., "Chinese", "English", "Japanese") in the manual toggle button.

### Fixed
- Ensured that no compilable code logic or configuration files were altered during the translation process.

## [0.3.0] - 2026-05-14
### Added
- **Persistent Selection State**: Checking a word in "Prep Management" now saves the state to the database. The selection persists even after closing the app.
- **Optimized Selection Logic**: The "Start Class" button on the home screen now automatically filters and only includes words that are "Checked" and "Not yet learned."
- **Loop-Learning Mode**: In class mode, reaching the last card and clicking "Next" will automatically loop back to the first card, facilitating repetitive practice.
- **Smart Language Detection**: The system automatically detects the accent based on input. A micro-toggle is provided for manual correction of ambiguous cases (e.g., Japanese Kanji vs. Chinese).

### Fixed
- **Android Permission Fix**: Added Android Internet permission to ensure Unsplash image searches work in Release mode.
- **Pronunciation Accuracy Fix**: Optimized language detection to prevent Japanese Kanji (e.g., "自転車") from being misidentified as Chinese.

### Changed
- **UI Optimization**: Renamed the "Need more practice" button to the more intuitive "Next" and updated it with an arrow icon to reduce parental pressure and improve navigation flow.

## [0.2.0] - 2026-05-13
### Added
- **Phase 3**: Developed `ClassView` (Flashcard UI) for full-screen immersive teaching.
- **Phase 3**: Integrated `flutter_tts` for automatic pronunciation and implemented exposure count tracking logic.
- Support for `sqflite` configuration on Windows and Linux desktop.

### Changed
- **Feature Update**: Removed "AI Image Generation" and related settings pages.
  - *Reasoning*: Due to a lack of stable free APIs, the focus has returned to the stable and high-quality Unsplash image library to ensure a smooth teaching experience.

### Fixed
- Upgraded `SettingsNotifier` syntax to the latest `Notifier` to fix compilation errors.

## [0.1.0] - 2026-05-12
### Added
- Project Initialization: Configured core dependencies such as `flutter_tts`, `sqflite`, `riverpod`, and `http`.
- **Phase 1 & 2**: Completed basic management interfaces including `SettingsView`, `AddPrepView`, and `PrepListView`.
- Implemented core logic for `ApiService` and `DatabaseService`.
