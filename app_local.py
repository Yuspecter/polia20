import streamlit as st, pandas as pd
from math import sqrt

# ---------- 定義 ----------
ISSUES = {
    "tax_raise"       : "増税に賛成？",
    "defense_spend"   : "防衛費増に賛成？",
    "same_sex"        : "同性婚を認める？",
    "nuclear_restart" : "原発再稼働に賛成？",
    "immigration"     : "移民受け入れに前向き？",
    "carbon_tax"      : "炭素税導入に賛成？",
    "child_budget"    : "子育て予算を増やす？"
}
CHOICES = {"はい": 1.0, "いいえ": -1.0, "どちらとも言えない": 0.0}
ISSUE_KEYS = list(ISSUES.keys())

# ---------- データ ----------
df = pd.read_csv("profiles.csv")

# ---------- 質問 UI ----------
st.title("🗳️ 思想マッチ議員診断（ローカル改良版）")
if "ans" not in st.session_state:
    st.session_state.ans = {}

unans = [k for k in ISSUE_KEYS if k not in st.session_state.ans]

if unans:
    k = unans[0]
    st.subheader(f"Q{len(st.session_state.ans)+1}. {ISSUES[k]}")
    c = st.radio("選択してください", CHOICES.keys(), key=k)
    if st.button("回答！"):
        st.session_state.ans[k] = CHOICES[c]
        st.rerun()
else:
    user_vec = st.session_state.ans

    # ------- 類似度（cosine）→ 0–100% へ -------
    def cosine(a,b):
        num = sum(a[k]*b[k] for k in ISSUE_KEYS)
        den = sqrt(sum(a[k]**2 for k in ISSUE_KEYS))*sqrt(sum(b[k]**2 for k in ISSUE_KEYS))
        return 0 if den==0 else num/den

    df["raw"]   = df.apply(lambda r: cosine(user_vec, r), axis=1)
    df["score"] = ((df["raw"] + 1) / 2 * 100).round()      # -1〜1 → 0〜100
    top5 = df.nlargest(5, "score")

    # ------- 結果カード -------
    st.success("あなたに近い議員 TOP5")
    for _, r in top5.iterrows():
        st.markdown(f"### {r['name']}（{r['party']}）　マッチ度：{int(r['score'])}%")
        st.write(r["policy"])
        st.divider()

    if st.button("もう一度やる"):
        st.session_state.clear()
        st.rerun()