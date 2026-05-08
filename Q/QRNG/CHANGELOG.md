# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-05-08

### Added
- Added `README.md` for better project navigation and quick start guidance.

## [1.1.0] - 2026-04-22

### Added
- Added a high-resolution visual Quantum Circuit diagram (`qrng_circuit.png`) for better clarity.

## [1.0.1] - 2026-04-22

### Changed
- Translated comments and print statements in `qrng.py` from Chinese to English for improved readability and internationalization.

## [1.0.0] - 2026-04-22

### Added
- Initial implementation of the Quantum Random Number Generator (QRNG).
- `qrng.py`: Script to generate single random bits and multi-bit numbers using Qiskit.
- `qrng_project.md`: Comprehensive documentation explaining quantum principles, circuit design, and implementation details.

### Changed
- Optimized the code to use `qiskit-aer` and explicit `transpile` steps for compatibility with the latest Qiskit versions.
