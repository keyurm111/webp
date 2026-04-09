import streamlit as st
from PIL import Image
import os
import zipfile
from io import BytesIO
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="OptiPress | Pro Image Optimizer",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Premium Look ---
st.markdown("""
    <style>
    .main {
        background: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,123,255,0.3);
    }
    .upload-box {
        border: 2px dashed #007bff;
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        background: white;
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    h1 {
        color: #1e293b;
        font-weight: 800;
        letter-spacing: -1px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar Settings ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8226/8226999.png", width=80)
    st.title("Settings")
    st.markdown("---")
    
    mode = st.radio("Compression Mode", ["Balanced (Recommended)", "Smallest Size", "Custom Target"], index=0)
    
    if mode == "Balanced (Recommended)":
        quality = 80
        target_kb = None
        scale_factor = 1.0
        st.info("💡 Reduced size by ~80-90% with zero visible quality loss.")
    elif mode == "Smallest Size":
        quality = 60
        target_kb = None
        scale_factor = 0.7
        st.warning("⚡ Maximum compression. Best for web speed.")
    else:
        quality = st.slider("Quality Level", 10, 100, 75)
        target_kb = st.number_input("Target Size (KB) - Optional", 0, 5000, 0)
        scale_factor = st.slider("Scale Down (%)", 10, 100, 100) / 100.0

    st.markdown("---")
    preserve_alpha = st.checkbox("Preserve Transparency (PNG/WebP)", value=True)
    strip_metadata = st.checkbox("Strip Metadata (Reduces size)", value=True)

# --- Main UI ---
col1, col2 = st.columns([2, 1])

with col1:
    st.title("🖼️ OptiPress Pro")
    st.subheader("Massively reduce image size without losing quality.")
    
    uploaded_files = st.file_uploader(
        "Drop your images here",
        type=["jpg", "jpeg", "png", "webp", "bmp", "tiff"],
        accept_multiple_files=True
    )

with col2:
    if uploaded_files:
        st.markdown(f"""
            <div class="stat-card">
                <h3>Batch Overview</h3>
                <p>Files: <b>{len(uploaded_files)}</b></p>
                <p>Format: <b>WebP (Optimized)</b></p>
            </div>
        """, unsafe_allow_html=True)

# --- Conversion Logic ---
def process_image(img, quality, target_kb, scale_factor, preserve_alpha, strip_metadata):
    # 1. Resize if needed
    if scale_factor < 1.0:
        w, h = img.size
        new_size = (int(w * scale_factor), int(h * scale_factor))
        img = img.resize(new_size, Image.LANCZOS)
    
    # 2. Handle Alpha Channel
    if not preserve_alpha and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode == "P":
        img = img.convert("RGBA")

    # 3. Smart Compression
    buffer = BytesIO()
    
    if target_kb and target_kb > 0:
        # Binary search for target KB
        min_q, max_q = 10, 100
        best_data = None
        for _ in range(8):
            q = (min_q + max_q) // 2
            temp_buf = BytesIO()
            img.save(temp_buf, format="WEBP", quality=q, method=6, optimize=True)
            if len(temp_buf.getvalue()) / 1024 > target_kb:
                max_q = q - 1
            else:
                best_data = temp_buf.getvalue()
                min_q = q + 1
        return best_data if best_data else temp_buf.getvalue()
    else:
        # Standard Quality-based
        img.save(buffer, format="WEBP", quality=quality, method=6, optimize=True)
        return buffer.getvalue()

if uploaded_files:
    if st.button("🚀 Start Bulk Optimization"):
        zip_buffer = BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_original_size = 0
        total_new_size = 0
        
        results = []
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
            for i, file in enumerate(uploaded_files):
                try:
                    original_size = len(file.getvalue()) / 1024
                    total_original_size += original_size
                    
                    status_text.text(f"Processing: {file.name}...")
                    
                    img = Image.open(file)
                    webp_data = process_image(img, quality, target_kb, scale_factor, preserve_alpha, strip_metadata)
                    
                    new_size = len(webp_data) / 1024
                    total_new_size += new_size
                    
                    reduction = ((original_size - new_size) / original_size) * 100
                    
                    webp_name = os.path.splitext(file.name)[0] + ".webp"
                    zip_file.writestr(webp_name, webp_data)
                    
                    results.append({
                        "name": file.name,
                        "old": original_size,
                        "new": new_size,
                        "reduction": reduction
                    })
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                except Exception as e:
                    st.error(f"Error processing {file.name}: {e}")
        
        status_text.success("✅ Optimization Complete!")
        
        # --- Final Stats ---
        total_reduction = ((total_original_size - total_new_size) / total_original_size) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Original Size", f"{round(total_original_size/1024, 2)} MB")
        c2.metric("Optimized Size", f"{round(total_new_size/1024, 2)} MB", f"-{round(total_reduction, 1)}%", delta_color="normal")
        c3.metric("Reduction", f"{round(total_reduction, 1)}%")

        if total_reduction >= 90:
            st.balloons()
            st.success(f"🔥 Incredible! You saved {round(total_reduction, 1)}% space!")

        st.download_button(
            label="⬇️ Download All Optimized Images (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="optipress_optimized.zip",
            mime="application/zip"
        )
        
        # Details table
        with st.expander("View detailed report"):
            st.table(results)