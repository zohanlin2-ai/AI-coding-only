# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2026-04-21

### Added
- **DNN Face Detection**: Implemented ResNet-10 SSD face detector using OpenCV's DNN module for improved robustness.
- **Model Storage**: Added `models/` directory for Caffe model files.
- **Confidence Scoring**: Added real-time confidence percentage display for each detected face.

### Changed
- **UI Update**: Changed application title and added error status handling for missing model files.
- **Improved Eye Detection**: Now accurately performs eye detection within the DNN-sourced face bounding box.

## [1.2.0] - 2026-04-21

### Changed
- **Major Overhaul**: Switched from `face_recognition` (dlib) CLI to a **PySide6 GUI** based application.
- **Algorithm Change**: Replaced dlib-based face embeddings with **OpenCV Haar Cascades** for both Face and Eye detection.
- **Documentation**: Synchronized `face_recognition.md` with the new GUI implementation and dependencies.

## [1.1.0] - 2026-04-21

### Added
- Added `main.py`: Core real-time face recognition script with performance optimization (frame scaling).
- Added `encode.py`: Script for extracting and storing face embeddings from the `dataset` folder.
- Created `CHANGELOG.md`: To track project milestones and changes.

### Optimized
- `face_recognition.md`: Refactored documentation to be more professional, removed raw code snippets, and added Windows-specific installation guides and performance tips.

## [1.0.0] - 2026-04-21

### Added
- Initial project structure defined in `face_recognition.md`.
- Basic face recognition logic conceptualized.
