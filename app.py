import streamlit as st
from PIL import Image, ImageOps 
import os
import zipfile
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(page_title="OptiPress | Simple Image Optimizer", page_icon="🖼️", layout="centered")

# --- Minimalist CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .stButton>button {
        background: #007bff;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        width: 100%;
        border: none;
    }
    .stButton>button:hover { background: #0056b3; border: none; color: white; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #007bff; }
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

# --- Main Logic ---
st.title("🖼️ OptiPress")
st.write("Convert and compress images to WebP instantly.")

uploaded_files = st.file_uploader("", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)

def process_image(file, q, s, rot, alpha):
    with Image.open(file) as img:
        if rot: img = ImageOps.exif_transpose(img)
        
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
                
                webp = process_image(f, quality, scale, fix_rotation, keep_alpha)
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