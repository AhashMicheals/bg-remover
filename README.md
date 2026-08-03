# PureCut AI - AI Background Remover & Pure White Product Photography Studio

**PureCut AI** is a production-ready, full-stack web application designed for e-commerce store owners, Amazon/Shopify sellers, photographers, and studios. It automatically removes image backgrounds using `rembg` (U2Net AI model) and composites product subjects onto a pure white background (`#FFFFFF`) at high resolution (95% JPEG quality).

---

## 🌟 Key Features

- 📸 **Pure White Background Replacement**: Isolates foreground subjects and places them on a clean 100% white (`#FFFFFF`) canvas.
- ⚡ **Batch Processing**: Process up to 20 images simultaneously per job.
- 🛡️ **Strict Upload Limits & Security**: Enforces max 20MB per file, validates MIME magic bytes, sanitizes filenames, and cleans temporary files.
- 🎛️ **Interactive Split Preview**: Compare original photos with processed white-background outputs using a drag-and-drop comparison slider with zoom and fullscreen support.
- 📦 **Instant ZIP Batch Download**: Download single processed images or export full/selected batches into `Converted_Images.zip`.
- 🎨 **Modern SaaS Interface**: Built with responsive HTML5, CSS3 glassmorphism design, dark/light theme persistence, clipboard paste (`Ctrl+V`), and keyboard shortcuts.

---

## 📁 Folder Structure

```
background-remover/
├── frontend/
│   ├── index.html          # Main HTML5 UI markup
│   ├── css/
│   │   └── style.css       # Custom design system with light/dark variables & glassmorphism
│   ├── js/
│   │   └── app.js          # ES6 App controller, batch queue, polling & split slider
│   └── assets/
│       └── logo.svg        # Vector branding icon
├── backend/
│   ├── main.py             # FastAPI entry point & static server
│   ├── api/
│   │   └── routes.py       # API endpoints (/api/upload, /api/process, /api/status, etc.)
│   ├── services/
│   │   ├── background.py   # rembg background removal integration
│   │   ├── image.py        # Pillow white background composition & quality exporter
│   │   └── zip.py          # Zip archive packager
│   ├── uploads/            # Temporary upload storage
│   ├── outputs/            # Processed white background images
│   └── temp/               # Thumbnail previews & zip exports
├── requirements.txt        # Python backend dependencies
└── README.md               # Complete setup & deployment guide
```

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.12+**
- **pip** package installer

### 1. Create Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Application

Launch the FastAPI backend server:

```bash
python backend/main.py
```
*or using Uvicorn directly:*
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your web browser and navigate to:
👉 **`http://127.0.0.1:8000`**

The server will automatically host the API endpoints under `/api` and serve the frontend user interface at `/`.

---

## 📖 API Documentation

Once the backend is running, interactive Swagger API documentation is available at:
👉 `http://127.0.0.1:8000/docs`

### Primary Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload up to 20 image files (`multipart/form-data`) |
| `POST` | `/api/process` | Trigger batch background removal & white composition |
| `GET` | `/api/status/{job_id}` | Poll progress status, speed, and completed items |
| `GET` | `/api/preview/{job_id}/{image_id}/{type}` | Serve thumbnail, original, or processed preview |
| `GET` | `/api/download/{job_id}/{image_id}` | Download individual `{filename}_white.jpg` image |
| `GET` | `/api/download-zip/{job_id}` | Download `Converted_Images.zip` archive |
| `POST` | `/api/download-selected/{job_id}` | Download custom ZIP of selected image IDs |
| `DELETE` | `/api/cancel/{job_id}` | Cancel job and remove temporary files |

---

## 🔒 Security & Performance Features

- **Sanitized Filenames**: Guards against path traversal vulnerabilities.
- **Automatic TTL File Cleanup**: Orphaned temporary files and job directories are purged automatically after 1 hour.
- **Multithreaded AI Workers**: Processing is offloaded to a background `ThreadPoolExecutor` so the main FastAPI event loop remains responsive.

---

## 🔧 Deployment Instructions

### Docker Deployment
Create a `Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t purecut-ai .
docker run -p 8000:8000 purecut-ai
```

---

## ❓ Troubleshooting

1. **Model Download on First Run**:
   On the very first execution, `rembg` automatically downloads the `u2net` ONNX AI model (~170MB). Allow a few seconds for initial setup.
2. **OpenCV DLL issue on Linux**:
   If running on a headless Linux instance, install `libgl1-mesa-glx`:
   `apt-get update && apt-get install -y libgl1-mesa-glx`

---

&copy; 2026 PureCut AI. Built with FastAPI, rembg, Pillow & Vanilla JS.
