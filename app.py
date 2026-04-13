import streamlit as st
from PIL import Image, ImageOps 
try:
    from rembg import remove
except ImportError:
    remove = None
import os
import zipfile
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(page_title="OptiPress | Simple Image Optimizer", page_icon="🖼️", layout="centered")

# --- Minimalist CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background-color: #f8f9fa;
    }
    
    .stApp { background-color: #f8f9fa; }
    
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border-radius: 12px;
        height: 3.5em;
        font-weight: 600;
        width: 100%;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.2);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3);
        background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
        color: white;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #6366f1;
        font-weight: 700;
    }
    
    .stMarkdown h1 {
        background: linear-gradient(to right, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    /* Modern Card Style for File Uploader */
    [data-testid="stFileUploader"] {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Only for Settings ---
with st.sidebar:
    st.title("⚙️ Settings")
    mode = st.radio("Compression Level", ["Balanced", "Maximum (Smallest Size)", "Manual Control"], index=0)
    
    if mode == "Manual Control":
        quality = st.slider("Quality", 10, 100, 75)
        scale = st.slider("Resize (%)", 10, 100, 100) / 100.0
    elif mode == "Maximum (Smallest Size)":
        quality, scale = 50, 0.7
    else:
        quality, scale = 80, 1.0

    with st.expander("Advanced Tools"):
        fix_rotation = st.checkbox("Fix Photo Rotation", value=True)
        keep_alpha = st.checkbox("Keep Transparency", value=True)
        remove_bg = st.checkbox("Remove Background ✨", value=False, help="Automatically remove image backgrounds using AI.")
        
    if remove_bg and remove is None:
        st.sidebar.warning("⚠️ 'rembg' library not found. Background removal will be skipped.")

# --- Main Logic ---
st.title("🖼️ OptiPress")
st.write("Convert and compress images to WebP instantly.")

uploaded_files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, label_visibility="collapsed")

def process_image(file, q, s, rot, alpha, rm_bg):
    with Image.open(file) as img:
        if rot: img = ImageOps.exif_transpose(img)
        
        # Background Removal
        if rm_bg and remove:
            img = remove(img)
            # Ensure transparency is preserved if background is removed
            alpha = True 
        
        # Mode handling
        if img.mode in ("RGBA", "P") and not alpha:
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB" and not alpha:
            img = img.convert("RGB")

        if s < 1.0:
            img = img.resize((int(img.width * s), int(img.height * s)), Image.Resampling.LANCZOS)
        
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=q, method=6, optimize=True)
        return buf.getvalue()

if uploaded_files:
    if st.button("🚀 Start Compression"):
        zip_buf = BytesIO()
        t_orig, t_new = 0, 0
        
        with zipfile.ZipFile(zip_buf, "w") as zf:
            prog = st.progress(0)
            for i, f in enumerate(uploaded_files):
                orig_bytes = f.getvalue()
                t_orig += len(orig_bytes)
                
                webp = process_image(f, quality, scale, fix_rotation, keep_alpha, remove_bg)
                t_new += len(webp)
                
                zf.writestr(f"{os.path.splitext(f.name)[0]}.webp", webp)
                prog.progress((i + 1) / len(uploaded_files))
        
        # Result Summary
        st.success(f"Reduced size by {round((t_orig - t_new) / t_orig * 100, 1)}%!")
        
        col1, col2 = st.columns(2)
        col1.metric("Original", f"{round(t_orig/1024/1024, 2)} MB")
        col2.metric("New Size", f"{round(t_new/1024/1024, 2)} MB")

        st.download_button(
            "⬇️ Download Compressed Images (ZIP)",
            data=zip_buf.getvalue(),
            file_name="compressed_images.zip",
            mime="application/zip"
        )