import streamlit as st
import os
import fitz  # PyMuPDF
import pandas as pd

PDF_FOLDER = "pdfs"
CACHE_FILE = "resume_db.csv"

os.makedirs(PDF_FOLDER, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

def extract_name(text):
    lines = text.split('\n')
    for line in lines:
        if line.strip():
            return line.strip()
    return "不明"

def process_pdfs():
    data = []
    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith(".pdf"):
            path = os.path.join(PDF_FOLDER, filename)
            text = extract_text_from_pdf(path)
            name = extract_name(text)
            data.append({
                "ファイル名": filename,
                "名前": name,
                "テキスト全文": text
            })
    df = pd.DataFrame(data)
    df.to_csv(CACHE_FILE, index=False)
    return df

def load_or_create_db():
    if os.path.exists(CACHE_FILE):
        return pd.read_csv(CACHE_FILE)
    else:
        return process_pdfs()

def main():
    st.set_page_config(page_title="履歴書検索", layout="wide")
    st.title("📄 履歴書検索システム（Streamlit Cloud対応）")

    st.markdown("## 📤 履歴書PDFをアップロード")
    uploaded_files = st.file_uploader("PDFファイルを選択（複数可）", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        for file in uploaded_files:
            file_path = os.path.join(PDF_FOLDER, file.name)
            with open(file_path, "wb") as f:
                f.write(file.read())
        st.success(f"{len(uploaded_files)} 件のファイルをアップロードしました！")
        df = process_pdfs()
    else:
        df = load_or_create_db()

    st.markdown("## 🔍 キーワード検索（名前・内容）")
    keyword = st.text_input("検索ワード", "")

    if keyword:
        result = df[df.apply(lambda row:
            keyword.lower() in str(row.get("名前", "")).lower() or
            keyword.lower() in str(row.get("テキスト全文", "")).lower(), axis=1)]
    else:
        result = df

    st.markdown(f"### 👤 検索結果（{len(result)} 件）")
    for _, row in result.iterrows():
        with st.expander(f"{row['名前']} | {row['ファイル名']}"):
            st.write(row['テキスト全文'][:2000] + "...")
            pdf_path = os.path.join(PDF_FOLDER, row['ファイル名'])
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button("📎 PDFをダウンロード", f.read(), file_name=row["ファイル名"])

if __name__ == "__main__":
    main()