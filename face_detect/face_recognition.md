# Robust DNN 人臉與眼睛偵測系統 (PySide6 + OpenCV)

## 🎯 專案目標
升級為更強健的深度神經網路 (DNN) 偵測系統，並具備圖形化介面，達成以下功能：
- **DNN 高精度偵測**：採用 ResNet-10 SSD 模型，相較於 Haar Cascades，對人臉角度、遮蔽與光線變化的容忍度更高。
- **即時信心度顯示**：在偵測框上即時顯示模型對該人臉判定的信心百分比。
- **二階段偵測**：先透過 DNN 定位人臉，再於人臉感興趣區域 (ROI) 內使用 Haar Cascade 進行眼睛偵測。
- **現代化 UI 控制**：整合 PySide6 提供流暢的操作體驗與狀態回饋。

---

## 🏗️ 系統架構
本專案整合了 **Caffe 框架** 的預訓練模型與 **OpenCV DNN 模組**：
`Webcam 擷取` → `影像預處理 (Blob)` → `DNN 模型推論 (ResNet-10)` → `信心度過濾 (>0.5)` → `眼睛偵測 (Haar)` → `GUI 呈現`

---

## ⚙️ 環境準備與安裝

### 1. 必備套件
請安裝以下 Python 套件：
- `PySide6`：GUI 框架。
- `opencv-python`：影像處理與 DNN 模組。
- `numpy`：陣列與矩陣運算。

**安裝指令：**
```bash
pip install PySide6 opencv-python numpy
```

---

## 📂 專案結構與資源
為了讓 DNN 模型正常運作，必須維持以下結構：

```text
face_detect/
├── main.py       # 核心 GUI 程式碼
├── models/       # (重要) 存放深度學習模型檔
│   ├── deploy.prototxt
│   └── res10_300x300_ssd_iter_140000.caffemodel
├── CHANGELOG.md  # 專案版本紀錄
└── dataset/      # (預留)
```

---

## 🚀 使用方式
1. **確認模型檔案**：確保 `models/` 資料夾內已包含 `.prototxt` 與 `.caffemodel` 檔案。
2. **啟動主程式**：執行 `python main.py`。
3. **開啟攝影機**：點擊 **"Start Camera Stream"**。
4. **啟動強健偵測**：點擊 **"Enable Detection"**。若缺少模型檔，狀態列會顯示錯誤提示。

---

## 🔍 技術細節說明
- **影像預處理**：使用 `cv2.dnn.blobFromImage` 將影像縮放至 300x300 並進行均值減除 (Mean Subtraction)，以符合模型輸入要求。
- **信心度門檻**：預設設定為 `0.5`，低於此值的偵測結果將被忽略，以減少誤判。

---

## 📝 總結
此版本代表了從傳統特徵比對到**深度學習偵測**的重大演進。不僅大幅提升了在複雜環境下的偵測穩定性，也為後續加入情緒識別、人臉對齊等更進階的 AI 功能奠定了基礎。
