# PureCut AI - AI Background Remover Studio (Streamlit)

**PureCut AI** is a professional AI-powered background removal and product photography studio built with **Python & Streamlit**. It automatically isolates subjects from images using cutting-edge deep learning neural models (`rembg` / `u2net` / `isnet`) and composites them onto studio-grade pure white canvas (`#FFFFFF`), custom solid colors, transparent PNG, or custom backdrop images.

---

## 🌟 Key Features

- 📸 **Pure White Background (#FFFFFF)**: Standards-compliant clean white canvas for Amazon, Shopify, eBay, and e-commerce listings.
- 🎨 **Multi-Canvas Studio**: Choose Pure White, Transparent PNG, Custom Solid Colors (with color picker & presets), or Custom Backdrop Images.
- ⚡ **Batch Image Processing**: Upload and process up to 20 high-resolution images in a single batch with real-time progress indicators.
- 🔍 **Interactive Split-Screen Slider**: Compare original photos with AI-processed outputs using a responsive drag-and-drop comparison slider.
- 🧠 **Multi-Model AI Support**: Switch between `U2Net` (High Quality), `U2NetP` (Fast & Lightweight), and `IS-Net` (Precision Edges).
- 📦 **Instant ZIP Batch Download**: Download individual processed photos or export the entire batch as `Converted_Images.zip` in one click.
- 🔒 **100% Private & Local**: All AI inference runs locally on your machine without external cloud dependencies.

---

## 📁 Project Structure

```
bg-remover/
├── app.py                  # Main Streamlit Web Application
├── services/
│   ├── background.py       # AI model management & rembg inference
│   ├── image.py            # Pillow composition (white canvas, solid color, backdrop)
│   └── zip.py              # In-memory batch ZIP exporter
├── requirements.txt        # Python dependencies
└── README.md               # Documentation & Setup guide
```

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **pip** package installer

### 1. Activate Virtual Environment

**On Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Streamlit Application

Launch the studio with Streamlit:

```bash
streamlit run app.py
```

*or run with the venv python directly:*
```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

Your default web browser will automatically open:
👉 **`http://localhost:8501`**

---

## 💡 How to Use

1. **Upload Images**: Drag and drop up to 20 images (`JPG`, `PNG`, `WEBP`) or click the demo sample button.
2. **Configure Studio**: Select your replacement background (Pure White, Custom Color, Transparent, or Backdrop), AI model, and export quality in the sidebar.
3. **Click Process**: Hit `✨ Remove Backgrounds` to trigger batch processing.
4. **Compare & Inspect**: Switch to the **Interactive Comparison** tab to drag the split slider.
5. **Download**: Save single images or click `📦 Download All ZIP` to download the entire batch.
