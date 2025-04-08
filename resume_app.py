import streamlit as st
import os
import fitz  # PyMuPDF
import pandas as pd
import datetime

# ------------------------
# 初期設定
# ------------------------
PDF_FOLDER = "pdfs"
CACHE_FILE = "resume_db.csv"
FAV_FILE = "favorites.csv"
LOG_FILE = "upload_log.csv"

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

def extract_skills(text):
    skills = ['Python', 'Excel', 'SQL', 'Java', 'HTML', 'CSS', 'Photoshop']
    found = [s for s in skills if s.lower() in text.lower()]
    return ', '.join(found)

def log_upload(filename):
    time = datetime.datetime.now().isoformat()
    log_entry = pd.DataFrame([[filename, time]], columns=["ファイル名", "アップロード時刻"])
    if os.path.exists(LOG_FILE):
        log_entry.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else:
        log_entry.to_csv(LOG_FILE, index=False)

def load_favorites():
    if os.path.exists(FAV_FILE):
        return pd.read_csv(FAV_FILE)
    else:
        return pd.DataFrame(columns=["名前", "ファイル名"])

def save_favorite(name, filename):
    fav_df = load_favorites()
    if not ((fav_df["名前"] == name) & (fav_df["ファイル名"] == filename)).any():
        fav_df.loc[len(fav_df)] = [name, filename]
        fav_df.to_csv(FAV_FILE, index=False)

def process_pdfs():
    data = []
    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith(".pdf"):
            path = os.path.join(PDF_FOLDER, filename)
            text = extract_text_from_pdf(path)
            name = extract_name(text)
            skills = extract_skills(text)
            data.append({
                "ファイル名": filename,
                "名前": name,
                "スキル": skills,
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
    st.set_page_config(page_title="履歴書検索システム", layout="wide")
    st.title("📄 履歴書検索システム（完全版）")

    # パスワード認証
    password = st.text_input("🔒 パスワードを入力", type="password")
    if password != "admin123":
        st.warning("正しいパスワードを入力してください")
        st.stop()

    st.sidebar.markdown("### ⭐ お気に入り一覧")
    fav_df = load_favorites()
    for _, row in fav_df.iterrows():
        st.sidebar.write(f"✅ {row['名前']} ({row['ファイル名']})")

    st.markdown("## 📤 履歴書PDFをアップロード")
    uploaded_files = st.file_uploader("PDFファイルを選択（複数可）", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            file_path = os.path.join(PDF_FOLDER, file.name)
            with open(file_path, "wb") as f:
                f.write(file.read())
            log_upload(file.name)
        st.success(f"{len(uploaded_files)} 件のファイルをアップロードしました！")
        df = process_pdfs()
    else:
        df = load_or_create_db()

    st.markdown("## 🔍 キーワード検索（名前・全文・スキル）")
    keyword = st.text_input("検索ワード")

    if keyword:
        result = df[df.apply(lambda row:
            keyword.lower() in str(row.get("名前", "")).lower() or
            keyword.lower() in str(row.get("スキル", "")).lower() or
            keyword.lower() in str(row.get("テキスト全文", "")).lower(), axis=1)]
    else:
        result = df

    st.markdown(f"### 👤 検索結果（{len(result)} 件）")
    for _, row in result.iterrows():
        with st.expander(f"{row['名前']} | {row['スキル']} | {row['ファイル名']}"):
            st.write(row['テキスト全文'][:2000] + "...")
            pdf_path = os.path.join(PDF_FOLDER, row['ファイル名'])
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button("📎 PDFをダウンロード", f.read(), file_name=row["ファイル名"])
            if st.button(f"⭐ お気に入りに追加 - {row['名前']}", key=row['ファイル名']):
                save_favorite(row["名前"], row["ファイル名"])
                st.success("お気に入りに追加しました！")

    st.markdown("### 📥 検索結果をCSVでダウンロード")
    st.download_button("CSVダウンロード", result.to_csv(index=False), "search_result.csv")

if __name__ == "__main__":
    main()
