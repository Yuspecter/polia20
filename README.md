# 政治家アキネイター β

Streamlit 製の簡易マッチングアプリ。
ユーザーの思想的な回答から、近しいスタンスを持つ国会議員（衆参）を提示します。

## 構成
- `app.py`: Streamlit アプリ本体
- `members_ideology.csv`: 議員のイデオロギー（スコア）＋政策ラベル（仮）
- `member_base.csv`: スクレイピングで取得した氏名リスト（241人）
- `issues.yaml`: 問いとスコア軸の対応付け（例：同性婚 = same_sex）
- `data_pipeline/`: 衆参の議員名HTMLからCSV生成する補助スクリプト

## 使い方
```bash
# 初回セットアップ
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# アプリ起動
streamlit run app.py