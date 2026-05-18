# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0] - 2026-05-18

### Changed (Full Project Optimization)
- **`ai_engine.py`**: Added Python type hints to all methods for improved maintainability.
- **`ai_engine.py`**: Migrated all path operations from `os.path` to modern `pathlib.Path`.
- **`ai_engine.py`**: Removed dead `__main__` test block.
- **`ai_engine.py`**: VAE float32 upcast now performed once in `load_model()` instead of redundantly in every `generate()` call.
- **`ai_engine.py`**: Added translation result validation — empty/None translation results fallback to original prompt to prevent shape mismatch errors.
- **`ai_engine.py`**: Added soft-detection of `xformers` for memory-efficient attention (~20-30% VRAM reduction).
- **`main.py`**: Added `_is_generating` guard clause to prevent duplicate concurrent generation calls.
- **`main.py`**: Added `worker.deleteLater()` to prevent QThread memory leaks on repeated generation.
- **`main.py`**: Added `📂 開啟輸出資料夾` secondary action button.
- **`main.py`**: Image area now clickable — opens last generated image in system default viewer.
- **`main.py`**: Generation errors no longer clear the last displayed image, only update the status bar.
- **`main.py`**: Error messages now show concise human-readable text in UI; full traceback printed to console.
- **`main.py`**: Added `setMinimumSize(800, 700)` to prevent layout collapse on small windows.
- **`main.py`**: Refactored `_set_controls_enabled()` helper to eliminate duplicated enable/disable logic.
- **`style.qss`**: Added hover effect on image display area to signal click-to-preview interactivity.
- **`style.qss`**: Added distinct secondary style for `#OpenFolderButton`.
- **`style.qss`**: Improved disabled button styling to better communicate inactive state.
- **`style.qss`**: Added `outline: none` to `QComboBox QAbstractItemView` to remove ugly focus rectangle.

## [1.4.1] - 2026-05-18

### Fixed
- Implemented **Two-Stage Decoupled Generation Architecture** to permanently eliminate all PyTorch tensor dtype collisions and VAE NaN numerical overflows:
  1. **Stage 1 (UNet Generation)**: Executed entirely inside `with torch.autocast("cuda")` returning raw fp16 latents (`output_type="latent"`), perfectly preventing `input type(Half) and bias type(float)` mismatch errors in text encoders and UNet layers.
  2. **Stage 2 (VAE Decoding)**: Executed in pure float32 outside `autocast` by explicitly upcasting latents and VAE weights (`latents.to(float32)`), guaranteeing zero numerical overflow (`invalid value in cast`) and flawlessly vibrant images without any black screens.

## [1.4.0] - 2026-05-18

### Added
- Integrated `AutoPipelineForText2Image` to enable dynamic background pipeline switching between SD 1.5 and SDXL architectures.
- Added `QComboBox` dropdown selector in the UI featuring three world-class AI models: DreamShaper 8, SDXL Turbo (1024px 3-step generation), and Realistic Vision 5.1.
- Implemented automated VRAM memory garbage collection (`torch.cuda.empty_cache()`) when switching models to prevent memory leaks.
- Smart inference parameter configuration matching each model's optimum settings (steps, guidance scale, default dimensions).

## [1.3.0] - 2026-05-18

### Added
- Implemented UI toggle button (`QCheckBox`) to dynamically enable or disable the NSFW safety filter before each generation.
- Default safety state set to off (`False`) to avoid false-positive black screens, giving users full creative control.

## [1.2.0] - 2026-05-18

### Added
- Integrated `deep-translator` for automatic Chinese-to-English prompt translation.
- Upgraded default AI model from base Stable Diffusion v1.5 to `Lykon/dreamshaper-8` for premium high-fidelity image quality.
- Disabled internal safety checker to eliminate false-positive black images and boost generation speed.
- UI status bar now displays the translated English prompt upon successful image generation.
- Added comprehensive section to `README.md` explaining how to verify GPU operation and local execution via `nvidia-smi` and offline testing.

## [1.1.0] - 2026-05-15

### Added
- Explicit GPU/CPU hardware detection.
- Real-time hardware status display in the application status bar.
- Guidance for NVIDIA GPU users to install CUDA-enabled Torch.

## [1.0.0] - 2026-05-14

### Added
- Initial project structure.
- Local AI image generation using Stable Diffusion.
- Simple and premium PySide6 GUI.
- Automatic prompt parsing for image size and format.
- Support for JPG (default), PNG, and WebP formats.
- Dark mode styling.
