"""
PureCut AI - Professional AI Background Remover & Product Photography Studio
Full Streamlit Application
"""
import io
import time
import os
import sys
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw

# Add workspace directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st

from services.background import remove_background, AVAILABLE_MODELS
from services.image import (
    apply_background,
    export_image_to_bytes,
    generate_output_filename,
    sanitize_filename,
    create_thumbnail
)
from services.zip import create_zip_bytes

# Optional streamlit-image-comparison import
try:
    from streamlit_image_comparison import image_comparison
    HAS_IMAGE_COMPARISON = True
except ImportError:
    HAS_IMAGE_COMPARISON = False


# ==============================================================================
# PAGE CONFIGURATION & STYLES
# ==============================================================================
st.set_page_config(
    page_title="PureCut AI - Background Remover Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern Dark/Light responsive UI, gradient cards, badges, and buttons
st.markdown("""
<style>
    /* Global Font & Header adjustments */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.12) 50%, rgba(236, 72, 153, 0.12) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px 30px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
    }
    
    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        border-radius: 9999px;
        background: linear-gradient(135deg, #6366f1, #a855f7);
        color: white;
        margin-bottom: 10px;
    }
    
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0 0 6px 0;
        background: linear-gradient(135deg, #1e293b, #475569);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    @media (prefers-color-scheme: dark) {
        .app-title {
            background: linear-gradient(135deg, #f8fafc, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
    }
    
    .app-subtitle {
        font-size: 1.05rem;
        color: #64748b;
        margin: 0;
    }
    
    .stat-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(226, 232, 240, 0.2);
        border-radius: 12px;
        padding: 14px 18px;
        text-align: center;
    }
    
    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #6366f1;
    }
    
    .stat-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .image-card {
        border-radius: 12px;
        border: 1px solid rgba(226, 232, 240, 0.15);
        padding: 12px;
        background: rgba(255, 255, 255, 0.02);
        margin-bottom: 16px;
    }
    
    .stDownloadButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    
    .checkerboard-bg {
        background-image: linear-gradient(45deg, #e2e8f0 25%, transparent 25%), 
                          linear-gradient(-45deg, #e2e8f0 25%, transparent 25%), 
                          linear-gradient(45deg, transparent 75%, #e2e8f0 75%), 
                          linear-gradient(-45deg, transparent 75%, #e2e8f0 75%);
        background-size: 20px 20px;
        background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SAMPLE IMAGES GENERATION (FOR INSTANT TEST)
# ==============================================================================
@st.cache_data
def get_sample_image(sample_type: str = "product") -> Image.Image:
    """Generates synthetic high-contrast sample images for quick testing."""
    img = Image.new("RGB", (600, 600), (220, 230, 242))
    draw = ImageDraw.Draw(img)
    
    if sample_type == "product":
        # Draw a stylish sneaker / product shape
        draw.rectangle([100, 100, 500, 500], fill=(240, 240, 245))
        draw.ellipse([150, 200, 450, 420], fill=(239, 68, 68))
        draw.rectangle([180, 280, 420, 400], fill=(30, 41, 59))
        draw.ellipse([200, 310, 400, 370], fill=(255, 255, 255))
        draw.text((220, 335), "PureCut AI", fill=(15, 23, 42))
    elif sample_type == "portrait":
        # Draw a portrait silhouette avatar
        draw.ellipse([200, 150, 400, 350], fill=(245, 158, 11))
        draw.ellipse([120, 370, 480, 650], fill=(59, 130, 246))
    else:
        # Electronic gadget / watch
        draw.ellipse([170, 170, 430, 430], fill=(30, 41, 59))
        draw.ellipse([200, 200, 400, 400], fill=(15, 23, 42))
        draw.line([300, 300, 300, 240], fill=(16, 185, 129), width=8)
        draw.line([300, 300, 360, 300], fill=(16, 185, 129), width=6)
        
    return img


# ==============================================================================
# STATE INITIALIZATION
# ==============================================================================
if "processed_results" not in st.session_state:
    st.session_state.processed_results = []
if "batch_stats" not in st.session_state:
    st.session_state.batch_stats = {"count": 0, "total_time": 0.0, "avg_time": 0.0}
if "processing_in_progress" not in st.session_state:
    st.session_state.processing_in_progress = False


# ==============================================================================
# SIDEBAR - STUDIO SETTINGS
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Studio Controls")
    
    st.markdown("#### 🎨 Canvas & Background")
    bg_mode_label = st.radio(
        "Replacement Background",
        options=["Pure White (#FFFFFF)", "Custom Solid Color", "Transparent (PNG)", "Custom Background Image"],
        index=0,
        help="Pure White is ideal for Amazon/Shopify product photography. Transparent PNG retains alpha layer."
    )
    
    bg_mode = "white"
    custom_color_hex = "#FFFFFF"
    custom_bg_image = None
    
    if bg_mode_label == "Pure White (#FFFFFF)":
        bg_mode = "white"
        st.caption("Standard pure white `#FFFFFF` for e-commerce.")
    elif bg_mode_label == "Custom Solid Color":
        bg_mode = "color"
        col_c1, col_c2 = st.columns([1, 1])
        with col_c1:
            preset = st.selectbox("Presets", ["Custom", "Studio Gray (#F3F4F6)", "Soft Blue (#EFF6FF)", "Pastel Pink (#FFF1F2)", "Jet Black (#000000)"])
        with col_c2:
            preset_map = {
                "Studio Gray (#F3F4F6)": "#F3F4F6",
                "Soft Blue (#EFF6FF)": "#EFF6FF",
                "Pastel Pink (#FFF1F2)": "#FFF1F2",
                "Jet Black (#000000)": "#000000",
                "Custom": "#6366F1"
            }
            default_hex = preset_map.get(preset, "#6366F1")
            custom_color_hex = st.color_picker("Pick Color", value=default_hex)
    elif bg_mode_label == "Transparent (PNG)":
        bg_mode = "transparent"
        st.caption("Transparent alpha background for graphic design and overlays.")
    elif bg_mode_label == "Custom Background Image":
        bg_mode = "image"
        custom_bg_file = st.file_uploader("Upload Backdrop Image", type=["jpg", "jpeg", "png", "webp"], key="bg_upload")
        if custom_bg_file:
            custom_bg_image = Image.open(custom_bg_file)
            st.image(custom_bg_image, caption="Active Backdrop", use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🤖 AI Model & Refinement")
    
    model_choice = st.selectbox(
        "AI Neural Model",
        options=list(AVAILABLE_MODELS.keys()),
        format_func=lambda x: AVAILABLE_MODELS[x],
        index=0,
        help="U2Net provides high quality cutouts. U2NetP is faster. IS-Net offers fine edge segmentation."
    )
    
    with st.expander("Fine-Tuning & Edge Options"):
        edge_feather = st.slider("Edge Smoothing (Feather px)", min_value=0, max_value=5, value=0, help="Smooths sharp pixel edges")
        use_alpha_matting = st.checkbox("Alpha Matting (Hair & Fine Detail)", value=False, help="Improves hair and fur segmentation (slower)")
        
        fg_thresh = 240
        bg_thresh = 10
        erode_val = 10
        if use_alpha_matting:
            fg_thresh = st.slider("Foreground Threshold", 100, 255, 240)
            bg_thresh = st.slider("Background Threshold", 0, 100, 10)
            erode_val = st.slider("Erode Structure Size", 1, 30, 10)

    st.markdown("---")
    st.markdown("#### 💾 Export Format")
    
    default_fmt_idx = 1 if bg_mode == "transparent" else 0
    export_format = st.selectbox("File Format", ["JPG", "PNG", "WEBP"], index=default_fmt_idx)
    
    if bg_mode == "transparent" and export_format == "JPG":
        st.warning("⚠️ JPG does not support transparency. Output will have white background or please switch to PNG/WEBP.")

    quality = 95
    if export_format in ("JPG", "WEBP"):
        quality = st.slider("Compression Quality", min_value=70, max_value=100, value=95)

    suffix_tag = st.text_input("Filename Suffix", value="_nobg")

    st.markdown("---")
    if st.button("🧹 Clear All Results", use_container_width=True):
        st.session_state.processed_results = []
        st.session_state.batch_stats = {"count": 0, "total_time": 0.0, "avg_time": 0.0}
        st.rerun()


# ==============================================================================
# MAIN PAGE HEADER
# ==============================================================================
st.markdown("""
<div class="main-header">
    <span class="badge-pill">⚡ AI PRODUCT PHOTOGRAPHY STUDIO</span>
    <h1 class="app-title">AI Background Remover</h1>
    <p class="app-subtitle">Instantly remove backgrounds and composite studio-grade pure white (#FFFFFF), transparent, or custom canvas for products & portraits.</p>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# TABS INTERFACE
# ==============================================================================
tab_process, tab_compare, tab_docs = st.tabs(["🚀 Process Images", "🔍 Interactive Comparison", "📖 Features & Guide"])


# ==============================================================================
# TAB 1: UPLOAD & PROCESS
# ==============================================================================
with tab_process:
    col_up1, col_up2 = st.columns([3, 1])
    
    with col_up1:
        uploaded_files = st.file_uploader(
            "Upload images to remove background (Batch support up to 20 images)",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            accept_multiple_files=True,
            help="Drag and drop or select up to 20 high-resolution images"
        )
        
    with col_up2:
        st.markdown("##### ⚡ Quick Demo Test")
        sample_opt = st.selectbox("Try a sample:", ["None", "👟 Sneaker Product", "👤 Portrait Person", "⌚ Smart Watch"])
        use_sample = sample_opt != "None"

    # Gather images to process
    images_to_run: List[Tuple[str, Image.Image]] = []
    
    if uploaded_files:
        for f in uploaded_files[:20]:
            try:
                im = Image.open(f)
                images_to_run.append((f.name, im))
            except Exception as e:
                st.error(f"Error opening {f.name}: {e}")
                
    elif use_sample:
        sample_type = "product" if "Sneaker" in sample_opt else ("portrait" if "Portrait" in sample_opt else "watch")
        sample_img = get_sample_image(sample_type)
        images_to_run.append((f"sample_{sample_type}.jpg", sample_img))

    # Action Toolbar
    if images_to_run:
        st.markdown(f"**Loaded:** `{len(images_to_run)}` image(s) ready for processing.")
        
        col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 3])
        with col_btn1:
            start_btn = st.button("✨ Remove Backgrounds", type="primary", use_container_width=True)
            
        # Processing Execution
        if start_btn:
            results = []
            progress_bar = st.progress(0, text="Initializing AI Neural Model...")
            status_text = st.empty()
            
            t0 = time.time()
            total_items = len(images_to_run)
            
            for idx, (fname, raw_img) in enumerate(images_to_run):
                pct = int(((idx) / total_items) * 100)
                progress_bar.progress(pct, text=f"Processing ({idx+1}/{total_items}): {fname}...")
                status_text.markdown(f"⏳ **AI Isolating foreground for** `{fname}`...")
                
                try:
                    t_item_0 = time.time()
                    # 1. Background removal using rembg
                    rgba_cutout = remove_background(
                        raw_img,
                        model_name=model_choice,
                        alpha_matting=use_alpha_matting,
                        alpha_matting_foreground_threshold=fg_thresh,
                        alpha_matting_background_threshold=bg_thresh,
                        alpha_matting_erode_size=erode_val
                    )
                    
                    # 2. Composite background
                    final_img = apply_background(
                        rgba_cutout,
                        bg_mode=bg_mode,
                        bg_color_hex=custom_color_hex,
                        custom_bg_img=custom_bg_image,
                        edge_feather=edge_feather
                    )
                    
                    # 3. Export to bytes
                    out_fmt = "png" if (bg_mode == "transparent" and export_format == "JPG") else export_format
                    out_bytes, mime = export_image_to_bytes(final_img, output_format=out_fmt, quality=quality)
                    out_filename = generate_output_filename(fname, output_format=out_fmt, suffix=suffix_tag)
                    
                    item_duration = time.time() - t_item_0
                    
                    results.append({
                        "filename": fname,
                        "out_filename": out_filename,
                        "original_img": raw_img,
                        "rgba_img": rgba_cutout,
                        "processed_img": final_img,
                        "bytes": out_bytes,
                        "mime": mime,
                        "duration": item_duration,
                        "status": "Success",
                        "dimensions": f"{raw_img.width} × {raw_img.height}"
                    })
                except Exception as e:
                    results.append({
                        "filename": fname,
                        "out_filename": fname,
                        "original_img": raw_img,
                        "rgba_img": None,
                        "processed_img": None,
                        "bytes": None,
                        "mime": None,
                        "duration": 0.0,
                        "status": f"Failed: {str(e)}",
                        "dimensions": "N/A"
                    })
                    
            total_duration = time.time() - t0
            progress_bar.progress(100, text="Completed!")
            status_text.success(f"🎉 Successfully processed {len(results)} image(s) in {total_duration:.2f}s!")
            
            st.session_state.processed_results = results
            st.session_state.batch_stats = {
                "count": len(results),
                "total_time": total_duration,
                "avg_time": round(total_duration / max(len(results), 1), 2)
            }
            time.sleep(0.5)
            st.rerun()

    # Results Display
    if st.session_state.processed_results:
        st.markdown("---")
        st.markdown("### 🎯 Processed Results")
        
        # Stats summary row
        stats = st.session_state.batch_stats
        c_stat1, c_stat2, c_stat3, c_stat4 = st.columns(4)
        with c_stat1:
            st.markdown(f"""<div class="stat-box"><div class="stat-value">{stats['count']}</div><div class="stat-label">Total Images</div></div>""", unsafe_allow_html=True)
        with c_stat2:
            st.markdown(f"""<div class="stat-box"><div class="stat-value">{stats['total_time']:.1f}s</div><div class="stat-label">Total Time</div></div>""", unsafe_allow_html=True)
        with c_stat3:
            st.markdown(f"""<div class="stat-box"><div class="stat-value">{stats['avg_time']:.2f}s</div><div class="stat-label">Speed per Image</div></div>""", unsafe_allow_html=True)
        with c_stat4:
            # Batch ZIP Download Button
            zip_entries = [
                (res["out_filename"], res["bytes"]) 
                for res in st.session_state.processed_results 
                if res["status"] == "Success" and res["bytes"] is not None
            ]
            if zip_entries:
                zip_data = create_zip_bytes(zip_entries)
                st.download_button(
                    label=f"📦 Download All ZIP ({len(zip_entries)})",
                    data=zip_data,
                    file_name="Converted_Images.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # Image Gallery / Grid
        for idx, item in enumerate(st.session_state.processed_results):
            with st.container():
                st.markdown(f"""
                <div class="image-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 700; font-size: 1rem;">#{idx+1} {item['filename']}</span>
                        <span style="color: #64748b; font-size: 0.85rem;">{item['dimensions']} • {item['duration']:.2f}s</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if item["status"] == "Success":
                    col_orig, col_res, col_dl = st.columns([3, 3, 2])
                    
                    with col_orig:
                        st.caption("📷 Original Image")
                        st.image(item["original_img"], use_container_width=True)
                        
                    with col_res:
                        st.caption("✨ Processed Output")
                        st.image(item["processed_img"], use_container_width=True)
                        
                    with col_dl:
                        st.caption("📥 Download")
                        st.download_button(
                            label=f"💾 Save {item['out_filename']}",
                            data=item["bytes"],
                            file_name=item["out_filename"],
                            mime=item["mime"],
                            key=f"dl_single_{idx}",
                            use_container_width=True
                        )
                        st.info(f"**Format:** `{item['out_filename'].split('.')[-1].upper()}`\n\n**Size:** `{len(item['bytes']) / 1024:.1f} KB`")
                else:
                    st.error(f"Failed to process {item['filename']}: {item['status']}")
                st.markdown("---")


# ==============================================================================
# TAB 2: INTERACTIVE COMPARISON STUDIO
# ==============================================================================
with tab_compare:
    st.markdown("### 🔍 Before & After Interactive Comparison")
    
    valid_results = [r for r in st.session_state.processed_results if r["status"] == "Success"]
    
    if not valid_results:
        st.info("💡 Process some images in the 'Process Images' tab to unlock the interactive comparison slider!")
    else:
        selected_idx = st.selectbox(
            "Select image to inspect:",
            options=range(len(valid_results)),
            format_func=lambda i: f"#{i+1} - {valid_results[i]['filename']}"
        )
        
        target = valid_results[selected_idx]
        
        if HAS_IMAGE_COMPARISON:
            st.caption("Drag the split slider horizontally to inspect edges and background removal precision:")
            # Ensure images are in RGB mode for comparison tool
            orig_rgb = target["original_img"].convert("RGB")
            res_rgb = target["processed_img"].convert("RGB")
            image_comparison(
                img1=orig_rgb,
                img2=res_rgb,
                label1="Original Photo",
                label2="AI Processed Output",
                width=800,
                starting_position=50,
                show_labels=True,
                make_responsive=True,
                in_memory=True
            )
        else:
            # Side-by-side fallback view
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("#### 📷 Original")
                st.image(target["original_img"], use_container_width=True)
            with col_c2:
                st.markdown("#### ✨ Processed Studio Output")
                st.image(target["processed_img"], use_container_width=True)


# ==============================================================================
# TAB 3: FEATURES & DOCUMENTATION
# ==============================================================================
with tab_docs:
    st.markdown("""
    ### 🌟 PureCut AI - Studio Features
    
    - 📸 **Pure White Background Replacement**: Standard `#FFFFFF` canvas compliance for e-commerce (Amazon, eBay, Shopify).
    - ⚡ **Batch AI Processing**: Upload and process up to 20 images with real-time progress indicators.
    - 🎨 **Multi-Canvas Support**: Pure white, custom solid hex colors, transparent PNG, or custom backdrop replacement.
    - 🧠 **Multi-Model Support**:
      - `U2Net`: Highest quality general segmentation.
      - `U2NetP`: Lightweight high-speed segmentation.
      - `IS-Net`: High-precision edge & boundary detection.
      - `Silueta`: Compact model optimized for people & objects.
    - 📦 **Instant ZIP Batch Export**: Download all converted images in one click.
    - 🔒 **100% Local & Secure**: All AI models execute locally on your machine.
    """)
