import streamlit as st

st.set_page_config(
    page_title="Waic-戦績管理",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 Waic カードゲーム戦績管理システム")

st.markdown("""
## 📋 使い方

このアプリでは3つの機能を提供しています：

### 1. ⚔️ 戦績入力
対戦結果を記録します。
- シーズン、使用デッキ、相手デッキなどを入力
- 先攻/後攻、勝敗、決着ターンを記録
- 対戦メモの追加が可能

👉 左サイドバーの「**戦績入力**」をクリック

---

### 2. 📊 戦績閲覧
詳細な分析と統計を表示します。
- デッキ別パフォーマンス分析
- マッチアップ相性の確認
- シーズン・環境別の絞り込み
- 戦績一覧とCSVダウンロード

👉 左サイドバーの「**戦績閲覧**」をクリック

---

### 3. 🔍 選手データ検索
選手情報と戦績を検索します。
- 選手名での検索
- 所属チーム、使用デッキでのフィルタリング
- Twitter IDへのリンク

👉 左サイドバーの「**選手データ検索**」をクリック

---

## 🚀 はじめに

左側のサイドバーから使いたい機能を選択してください。
""")

# 簡易ステータス表示
st.markdown("---")
st.subheader("📈 クイック統計")

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
from streamlit.errors import StreamlitAPIException

# Secrets から設定を取得
if hasattr(st, 'secrets') and "spreadsheet_ids" in st.secrets and "war_record" in st.secrets["spreadsheet_ids"]:
    SPREADSHEET_ID = st.secrets["spreadsheet_ids"]["war_record"]
else:
    SPREADSHEET_ID = None

WORKSHEET_NAME = "シート1"
COLUMNS = ['season', 'date', 'environment', 'my_deck', 'my_deck_type', 'opponent_deck', 'opponent_deck_type', 'first_second', 'result', 'finish_turn', 'memo']

@st.cache_resource
def get_gspread_client():
    """Google Sheets クライアントを取得"""
    creds = None
    use_streamlit_secrets = False
    if hasattr(st, 'secrets'):
        try:
            if "gcp_service_account" in st.secrets:
                use_streamlit_secrets = True
        except StreamlitAPIException:
            pass 
    if use_streamlit_secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        return None
    try:
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets接続エラー: {e}")
        return None

def load_summary_data():
    """サマリー用にデータを読み込み"""
    if not SPREADSHEET_ID:
        return pd.DataFrame()
    
    client = get_gspread_client()
    if client is None:
        return pd.DataFrame()
    
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        df = get_as_dataframe(worksheet, evaluate_formulas=False, header=0, na_filter=True)
        
        if df.empty:
            return pd.DataFrame()
        
        # 必要な列のみ保持
        needed_cols = [col for col in COLUMNS if col in df.columns]
        df = df[needed_cols]
        
        # date型変換
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        return df
    except:
        return pd.DataFrame()

# データ読み込みと表示
try:
    df = load_summary_data()
    
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📝 総対戦数", len(df))
        
        with col2:
            if 'result' in df.columns:
                wins = len(df[df['result'] == '勝ち'])
                st.metric("🏆 勝利数", wins)
            else:
                st.metric("🏆 勝利数", "N/A")
        
        with col3:
            if 'result' in df.columns:
                wins = len(df[df['result'] == '勝ち'])
                win_rate = (wins / len(df) * 100) if len(df) > 0 else 0
                st.metric("📊 勝率", f"{win_rate:.1f}%")
            else:
                st.metric("📊 勝率", "N/A")
        
        with col4:
            if 'season' in df.columns:
                seasons = df['season'].dropna().unique()
                st.metric("🗓️ シーズン数", len(seasons))
            else:
                st.metric("🗓️ シーズン数", "N/A")
    else:
        st.info("💡 まだ戦績データがありません。「戦績入力」ページから対戦結果を記録しましょう！")
except Exception as e:
    st.info("💡 データ読み込み準備中...")

st.markdown("---")
st.caption("Waic カードゲーム戦績管理システム v2.0")
