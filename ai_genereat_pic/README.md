# Local AI Image Generator

一個簡約、高效且充滿現代感的 PC 端本地 AI 產圖工具。內建三大頂級開源模型庫（支援 DreamShaper 8、SDXL Turbo 光速 1024px 高畫質、Realistic Vision 真人寫實），讓您在不需要網路的情況下，直接在自己的電腦上自由切換畫師風格並生成令人驚豔的高品質圖片。

## 特色
- **完全本地化**：您的描述與生成的圖片永遠留在您的電腦上，保護隱私。
- **智慧翻譯**：內建 `deep-translator`，支援直接輸入中文描述，程式會自動精準轉譯為英文供 AI 運算。
- **多畫師切換**：介面設有「AI 畫家模型」下拉選單，可一鍵切換不同架構與風格的模型（包含 3 步光速出圖的 SDXL Turbo）。
- **自動快取回收**：動態切換模型時自動釋放舊顯存 (`empty_cache`)，確保系統流暢不崩潰。
- **動態審核切換**：介面設有「啟用 NSFW 安全過濾機制」按鈕，預設為關閉以防止誤判黑畫面，並允許一鍵開啟防護。
- **架構視覺化**：隨附完整的 [系統架構與流程圖](file:///C:/Users/zohan/.gemini/antigravity/brain/f3d74870-49c3-46e0-9119-4d0974128a2e/architecture.md)，詳細解析多執行緒通訊與兩階段解耦生成架構。同時隨附獨立網頁 [export_diagrams.html](file:///c:/Users/zohan/Documents/ai_test/ai_genereat_pic/export_diagrams.html) 供您隨時開啟列印匯出為高畫質圖檔或 PDF。
- **硬體偵測**：自動辨識顯卡支援，並在介面下方顯示目前的運算狀態（GPU 或 CPU）。
- **預設最佳化**：若未指定格式，預設儲存為 `jpg` 以節省空間。
- **現代化介面**：深色模式 premium 設計，提供流暢的互動體驗。

## 系統需求
- **作業系統**：Windows 10/11
- **硬體推薦**：
    - NVIDIA GPU (4GB+ VRAM) 以獲得最佳效能。
    - 至少 16GB RAM。
    - 5GB 以上的硬碟空間（用於存放模型）。

## 安裝與執行

1. **安裝依賴**：
   ```bash
   pip install -r requirements.txt
   ```

2. **(推薦) 啟用 NVIDIA 顯卡加速**：
   如果您有 NVIDIA 顯卡，執行以下指令以獲得 10 倍以上的生成速度：
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126 --force-reinstall
   ```

3. **啟動程式**：
   ```bash
   python main.py
   ```

3. **初次執行**：
   程式會自動從 Hugging Face 下載 Stable Diffusion 模型權重，這可能需要一些時間（取決於您的網速）。

## 使用方式
在輸入框中描述您想要生成的圖片，您可以包含：
- **風格**：例如「油畫風格」、「寫實」、「賽博龐克」。
- **尺寸**：例如 `512x512` 或 `1024x1024`。
- **格式**：例如 `png`, `jpg`, `webp`。

**範例**：
> 一個在霓虹燈下的未來城市, 賽博龐克風格, 1024x768, png

## 🔬 如何驗證顯卡運作與本地端運算

在 Windows 系統中，傳統的「工作管理員」預設顯示的 3D 圖表無法精準捕捉 AI 的張量核心 (Tensor Core) 運算流量。為了確保運算完全在本地端 GPU 發生，建議透過以下兩種專業方式驗證：

### 1. 斷網測試 (離線驗證)
當初次下載模型完成後，您可以**直接關閉網路 (Wi-Fi 或拔掉網線)**，然後點選「開始生成」。圖片依然會在數秒內完美產出，證明所有計算均在本地端硬體獨立完成，無任何雲端傳輸。

### 2. 使用 NVIDIA 官方指令監控 (硬體底層監控)
開啟額外的終端機 (PowerShell)，在產圖前與產圖時執行以下指令監控：
```powershell
nvidia-smi -l 1
```
**觀察重點**：
- **耗電量 (`Pwr:Usage`)**：產圖瞬間瓦數會自待機的 20W~30W 暴衝至 **100W~250W+**，顯示 GPU 晶片正滿載運轉發熱。
- **顯示記憶體 (`VRAM`)**：表格下方 `Processes` 列表會顯示 `python.exe` 正在佔用約 **3GB ~ 4.5GB** 的顯示記憶體。

## 授權
MIT License
