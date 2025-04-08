import streamlit as st
import os
import fitz  # PyMuPDF
import pandas as pd
import datetime
import base64
import re

# ------------------------
# 初期設定
# ------------------------
PDF_FOLDER = "pdfs"
CACHE_FILE = "resume_db.csv"
FAV_FILE = "favorites.csv"
LOG_FILE = "upload_log.csv"
MEMO_FILE = "interview_notes.csv"

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

def remove_favorite(name, filename):
    fav_df = load_favorites()
    fav_df = fav_df[~((fav_df["名前"] == name) & (fav_df["ファイル名"] == filename))]
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

def load_memos():
    if os.path.exists(MEMO_FILE):
        return pd.read_csv(MEMO_FILE)
    else:
        return pd.DataFrame(columns=["名前", "ファイル名", "メモ", "評価", "ステータス"])

def save_memo(name, filename, memo, score, status):
    df = load_memos()
    df = df[~((df["名前"] == name) & (df["ファイル名"] == filename))]
    df.loc[len(df)] = [name, filename, memo, score, status]
    df.to_csv(MEMO_FILE, index=False)

def get_memo_info(name, filename):
    df = load_memos()
    match = df[(df["名前"] == name) & (df["ファイル名"] == filename)]
    if not match.empty:
        return match.iloc[0]["メモ"], match.iloc[0]["評価"], match.iloc[0]["ステータス"]
    return "", "", ""

def highlight_keywords(text, keywords):
    if not keywords:
        return text
    escaped_keywords = [re.escape(k) for k in keywords.split()]
    pattern = re.compile(r"(" + "|".join(escaped_keywords) + r")", re.IGNORECASE)
    highlighted = pattern.sub(r'<mark>\1</mark>', text)
    return highlighted

def main():
    st.set_page_config(page_title="社内 求人管理システム", layout="wide")
    st.title("📄 社内 求人管理システム")

    password = st.text_input("🔒 パスワードを入力", type="password")
    if password != "cyberlead2024":
        st.warning("正しいパスワードを入力してください")
        st.stop()

    st.sidebar.markdown("### ⭐ お気に入り一覧")
    fav_df = load_favorites()
    for _, row in fav_df.iterrows():
        st.sidebar.write(f"✅ {row['名前']} ({row['ファイル名']})")
        if st.sidebar.button(f"❌ 削除 - {row['名前']}", key=f"remove_{row['ファイル名']}"):
            remove_favorite(row['名前'], row['ファイル名'])
            st.experimental_rerun()

    uploaded_files = st.file_uploader("📤 履歴書PDFをアップロード（複数可）", type="pdf", accept_multiple_files=True)
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

    keyword1 = st.text_input("OR検索ワード（スペース区切りで複数指定可）")
    keyword2 = st.text_input("AND検索ワード（スペース区切りで複数指定可）")
    keyword3 = st.text_input("除外ワード（スペース区切りで複数指定可）")

    def match_keywords(row):
        text = " ".join([str(row.get("名前", "")), str(row.get("スキル", "")), str(row.get("テキスト全文", ""))]).lower()
        or_ok = any(k.lower() in text for k in keyword1.split()) if keyword1 else True
        and_ok = all(k.lower() in text for k in keyword2.split()) if keyword2 else True
        not_ok = all(k.lower() not in text for k in keyword3.split()) if keyword3 else True
        return or_ok and and_ok and not_ok

    result = df[df.apply(match_keywords, axis=1)]

    st.markdown(f"### 👤 検索結果（{len(result)} 件）")
    for _, row in result.iterrows():
        memo_text, score_text, status_text = get_memo_info(row['名前'], row['ファイル名'])
        st.markdown(f"""
        <div style='background-color: #1e1e1e; color: #ffffff; padding: 10px; margin: 8px 0; border-radius: 10px; border: 1px solid #444; box-shadow: 0 0 6px rgba(255,255,255,0.03); font-size: 14px;'>
            <table style='width: 100%;'>
                <tr><td style='width: 25%;'><strong>🧑‍💼 名前:</strong></td><td>{row['名前']}</td></tr>
                <tr><td><strong>🧠 スキル:</strong></td><td>{row['スキル']}</td></tr>
                <tr><td><strong>📎 ファイル名:</strong></td><td>{row['ファイル名']}</td></tr>
                <tr><td><strong>📒 面談メモ:</strong></td><td>{memo_text}</td></tr>
                <tr><td><strong>⭐ 評価:</strong></td><td>{score_text}</td></tr>
                <tr><td><strong>📌 ステータス:</strong></td><td>{status_text}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📄 履歴書テキストを全文表示＆編集"):
            highlighted_text = highlight_keywords(row['テキスト全文'], f"{keyword1} {keyword2}")
            st.markdown(f"<div style='background-color:#fff;border:1px solid #ccc;padding:10px;height:400px;overflow-y:scroll;color:#000'>{highlighted_text}</div>", unsafe_allow_html=True)
            with open(os.path.join(PDF_FOLDER, row['ファイル名']), "rb") as f:
                st.download_button("📎 PDFをダウンロード", f.read(), file_name=row["ファイル名"])
            memo = st.text_area("📝 面談メモを入力", value=memo_text, key=f"memo_{row['ファイル名']}")
            score = st.selectbox("⭐ 評価", ["", "A", "B", "C"], index=["", "A", "B", "C"].index(score_text) if score_text in ["A", "B", "C"] else 0, key=f"score_{row['ファイル名']}")
            status = st.selectbox("📌 ステータス", ["", "通過", "保留", "不採用"], index=["", "通過", "保留", "不採用"].index(status_text) if status_text in ["通過", "保留", "不採用"] else 0, key=f"status_{row['ファイル名']}")
            if st.button("💾 メモ保存", key=f"save_{row['ファイル名']}"):
                save_memo(row['名前'], row['ファイル名'], memo, score, status)
                st.success("保存しました")

    st.markdown("### 📊 スキル別保有人数")
    skill_counts = df["スキル"].str.split(', ').explode().value_counts()
    for skill, count in skill_counts.items():
        st.write(f"{skill}: {count}人")

    st.markdown("### 📈 検索結果をCSVでダウンロード")
    st.download_button("CSVダウンロード", result.to_csv(index=False), "search_result.csv")

if __name__ == "__main__":
    main()
