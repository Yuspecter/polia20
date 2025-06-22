# app_gpt.py ── Streamlit × GPT-4o mini 〔Slider & Free-text 版〕
import os, re, json, urllib.parse
import pandas as pd
import streamlit as st
import openai

# ------------------ 設定 ------------------
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ISSUES = {
    "tax_raise":        "増税に賛成度",
    "defense_spend":    "防衛費の増額賛成度",
    "same_sex":         "同性婚を認めるべき度",
    "nuclear_restart":  "原発再稼働賛成度",
    "immigration":      "移民受け入れ前向き度",
    "carbon_tax":       "炭素税導入賛成度",
    "child_budget":     "子育て予算を増やすべき度",
}
SLIDER_INFO = "← 強い反対                                                  強い賛成 →"

WEIGHT  = [5, 4, 3, 2, 1]          # 累計ランキング用ポイント
LOG_CSV = "match_log.csv"

# ---------------- GPT 要約（キャッシュ） ----------------
@st.cache_data(show_spinner=False)
def gpt_policy_digest(text: str) -> str:
    prompt = f"次の政策説明を25字以内で一文要約してください:\n{text}"
    rsp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=60,
    )
    return rsp.choices[0].message.content.strip()

# ---------------- Streamlit ----------------
st.set_page_config("思想マッチ議員診断", "🗳️", layout="centered")
st.title("🗳️ 思想マッチ議員診断 β")

# セッション初期化
for key in ("answers", "notes"):
    if key not in st.session_state:
        st.session_state[key] = {}

# ---------- 質問 ----------
unans = [k for k in ISSUES if k not in st.session_state["answers"]]
if unans:
    k = unans[0]
    st.subheader(f"Q.{len(st.session_state['answers'])+1}　{ISSUES[k]}")
    val = st.slider(SLIDER_INFO, -1.0, 1.0, 0.0, 0.2, key=f"slider_{k}")
    txt = st.text_area("自由記述（任意）", placeholder="あなたの考えを自由に書いてください", key=f"note_{k}")
    if st.button("次へ"):
        st.session_state["answers"][k] = round(val, 2)
        if txt.strip():
            st.session_state["notes"][k] = txt.strip()
        st.rerun()
    st.stop()

# ---------- 結果 ----------
user_vec   = st.session_state["answers"]          # 数値辞書
user_notes = st.session_state["notes"]           # テキスト辞書（空可）
df = pd.read_csv("profiles.csv").head(20)

# 候補側プロンプト化
def row_prompt(r):
    v = {k: r[k] for k in ISSUES}
    return f"{r['name']}（{r['party']}）{v}:{r['policy'][:50]}…"

cand_prompt = "\n".join(row_prompt(r) for _, r in df.iterrows())

system_msg = (
    "あなたは政治ジャーナリスト兼データサイエンティスト。\n"
    "ユーザーの数値ベクトル・自由記述と候補 CSV 情報を比較し、類似度が高い順に5名選んで "
    '{"items":[{ "name":"◯◯（党名）","score":0.92,"reason":"30字"}...] } '
    "のみを JSON で返却してください。score は 0–1 の実数。"
)

user_msg = (
    "【ユーザーベクトル】\n" + json.dumps(user_vec, ensure_ascii=False) + "\n\n" +
    "【ユーザー自由記述（無い項目は空文字）】\n" + json.dumps(user_notes, ensure_ascii=False) + "\n\n" +
    "【候補議員 20 名】\n" + cand_prompt
)

with st.spinner("Politics AI🤖 ががんばって考えています…😖"):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
top_items = json.loads(resp.choices[0].message.content)["items"]

# ---------- ログ更新 ----------
def update_log(items):
    if not os.path.exists(LOG_CSV):
        pd.DataFrame(columns=["name", "points"]).to_csv(LOG_CSV, index=False)
    log_df = pd.read_csv(LOG_CSV)
    for rank, it in enumerate(items[:5]):
        name = re.sub(r"（.*?）", "", it["name"])
        pts  = WEIGHT[rank]
        if name in log_df["name"].values:
            log_df.loc[log_df["name"] == name, "points"] += pts
        else:
            log_df = pd.concat([log_df, pd.DataFrame([{"name": name, "points": pts}])])
    log_df.to_csv(LOG_CSV, index=False)

update_log(top_items)

# ---------- 要約取得 ----------
strip_party = lambda s: re.sub(r"（.*?）", "", s).strip()
policies = {strip_party(r["name"]): r["policy"] for _, r in df.iterrows()}

with st.spinner("政策要約を生成中…"):
    summaries = {
        it["name"]: gpt_policy_digest(policies[strip_party(it["name"])])
        for it in top_items
    }

# ---------- カード表示 ----------
st.success("あなたに近い議員 TOP5")
for it in top_items:
    full = it["name"]
    base = strip_party(full)
    party = re.search(r"（(.*?)）", full)
    party = party.group(1) if party else ""

    st.markdown(
        f"### {base}（{party}） "
        f"<span style='color:#ff6600;font-weight:bold'>マッチ度：{it['score']*100:.0f}%</span>",
        unsafe_allow_html=True,
    )
    st.write("**理由**：", it["reason"])
    st.write("**政策要約**：", summaries[full])

    wiki   = f"https://ja.wikipedia.org/wiki/{urllib.parse.quote(base)}"
    google = f"https://www.google.com/search?q={urllib.parse.quote_plus(base + ' 公式サイト')}"
    c1, c2 = st.columns(2)
    c1.link_button("📚 Wikipedia", wiki)
    c2.link_button("🔗 公式サイト検索", google)
    st.divider()

# ---------- 累計ランキング TOP3 ----------
if os.path.exists(LOG_CSV):
    rank_df = (
        pd.read_csv(LOG_CSV)
        .sort_values("points", ascending=False)
        .head(3)
        .reset_index(drop=True)
    )
    medals = ["🥇", "🥈", "🥉"]
    st.markdown("## 🏆 マッチ累計ランキング TOP3")
    for i, row in rank_df.iterrows():
        base = row["name"]
        wiki = f"https://ja.wikipedia.org/wiki/{urllib.parse.quote(base)}"
        google = f"https://www.google.com/search?q={urllib.parse.quote_plus(base + ' 公式サイト')}"
        st.markdown(f"{medals[i]} **{base}** — 累計ポイント {int(row['points'])}")
        c1, c2 = st.columns(2)
        c1.link_button("📚 Wiki", wiki)
        c2.link_button("🔗 検索", google)

# ---------- リセット ----------
if st.button("もう一度やる"):
    st.session_state["answers"] = {}
    st.session_state["notes"]   = {}
    st.rerun()
