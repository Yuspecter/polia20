# app_gpt.py  ── Streamlit × GPT4o マッチング版
import os, json, pandas as pd, streamlit as st, openai

# ----------------- 設定 -----------------
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ISSUES = {
    "tax_raise":        "増税に賛成ですか？",
    "defense_spend":    "防衛費の増額に賛成ですか？",
    "same_sex":         "同性婚を認めるべきですか？",
    "nuclear_restart":  "原発再稼働に賛成ですか？",
    "immigration":      "移民受け入れに前向きですか？",
    "carbon_tax":       "炭素税導入に賛成ですか？",
    "child_budget":     "子育て予算を大幅に増やすべきですか？"
}
CHOICES = {"はい👌": 1.0, "いいえ🙂‍↔️": -1.0, "どちらとも言えない🤔": 0.0}

# --------------- セッション初期化 ----------------
if "answers" not in st.session_state:
    st.session_state.answers = {}

st.title("🗳️ 思想マッチ議員診断 β")

# 1) 質問表示 or 2) 結果表示
unanswered = [k for k in ISSUES if k not in st.session_state.answers]

if unanswered:
    q_key = unanswered[0]                 # 次の質問
    st.subheader(f"Q.{len(st.session_state.answers)+1} {ISSUES[q_key]}")
    ans = st.radio("選択してください", list(CHOICES.keys()))
    if st.button("回答！"):
        st.session_state.answers[q_key] = CHOICES[ans]
        st.rerun()
else:
    # ------- GPT へ丸投げしてマッチング --------
    user_vec = st.session_state.answers
    df = pd.read_csv("profiles.csv").head(20)

    issues = list(ISSUES.keys())
    def row_to_prompt(r):
        vec = {k: r[k] for k in issues}
        return f"{r['name']}（{r['party']}）{vec} : {r['policy'][:50]}…"
    cand_prompt = "\n".join(row_to_prompt(r) for _, r in df.iterrows())

    system_msg = "あなたは政治ジャーナリスト。ユーザーに近い議員トップ5を選びJSONで返す。"
    user_msg = (
        f"【ユーザーベクトル】\n{json.dumps(user_vec, ensure_ascii=False)}\n\n"
        "【候補議員 20 名】\n" + cand_prompt +
        '\n\n返答は {"items":[{ "name":"◯◯","score":0.85,"reason":"30字"}...]} のみ。'
    )

    with st.spinner("AIがマッチング中…"):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":system_msg},
                {"role":"user","content":user_msg}
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type":"json_object"},
        )
    result = json.loads(resp.choices[0].message.content)["items"]

    st.success("あなたに近い議員 TOP5")
    for r in result:
        st.markdown(f"### {r['name']}（マッチ度：{r['score']*100:.0f}%）")
        st.write(r["reason"])
        st.divider()

    if st.button("もう一度やる"):
        st.session_state.answers = {}
        st.rerun()