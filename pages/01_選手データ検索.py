import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
from streamlit.errors import StreamlitAPIException

st.set_page_config(layout="wide", page_title="選手データ検索")

# --- 定数定義 ---
# 選手データ用のスプレッドシートIDを設定してください
# 例: PLAYER_SPREADSHEET_ID = "1ABC...XYZ"
PLAYER_SPREADSHEET_ID = ""  # ここに選手データのスプレッドシートIDを入力
PLAYER_WORKSHEET_NAME = "シート1"  # シート名を適宜変更してください

# --- Google Sheets 連携 ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

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
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        try:
            creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
        except Exception as e:
            st.error(f"サービスアカウントの認証情報ファイル (service_account.json) の読み込みに失敗しました: {e}")
            return None
    
    try:
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheetsへの接続に失敗しました: {e}")
        return None

@st.cache_data(ttl=300)  # 5分間キャッシュ
def load_player_data(spreadsheet_id, worksheet_name):
    """選手データを読み込み"""
    if not spreadsheet_id:
        return pd.DataFrame()
    
    client = get_gspread_client()
    if client is None:
        st.error("Google Sheetsに接続できませんでした。")
        return pd.DataFrame()
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        df = get_as_dataframe(worksheet, evaluate_formulas=False, header=0, na_filter=True)
        
        # 空の行を削除
        df = df.dropna(how='all')
        
        # 空の列を削除
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

# --- メイン画面 ---
def main():
    st.title("🔍 選手データ検索")
    
    # スプレッドシートIDの設定チェック
    if not PLAYER_SPREADSHEET_ID:
        st.warning("⚠️ スプレッドシートIDが設定されていません。")
        st.info("""
        **設定方法:**
        1. このファイル（`pages/01_選手データ検索.py`）を開く
        2. `PLAYER_SPREADSHEET_ID` に選手データのスプレッドシートIDを設定
        3. 必要に応じて `PLAYER_WORKSHEET_NAME` も変更
        
        **スプレッドシートIDの取得方法:**
        - Google SheetsのURL: `https://docs.google.com/spreadsheets/d/【ここがID】/edit`
        """)
        
        # テスト用のスプレッドシートID入力
        with st.expander("一時的にスプレッドシートIDを入力"):
            temp_id = st.text_input("スプレッドシートID", key="temp_spreadsheet_id")
            temp_sheet = st.text_input("シート名", value="シート1", key="temp_sheet_name")
            if st.button("読み込み"):
                if temp_id:
                    st.session_state['temp_spreadsheet_id'] = temp_id
                    st.session_state['temp_worksheet_name'] = temp_sheet
                    st.rerun()
        
        if 'temp_spreadsheet_id' in st.session_state:
            spreadsheet_id = st.session_state['temp_spreadsheet_id']
            worksheet_name = st.session_state['temp_worksheet_name']
        else:
            return
    else:
        spreadsheet_id = PLAYER_SPREADSHEET_ID
        worksheet_name = PLAYER_WORKSHEET_NAME
    
    # データ読み込み
    with st.spinner("データを読み込み中..."):
        df = load_player_data(spreadsheet_id, worksheet_name)
    
    if df.empty:
        st.warning("データがありません。スプレッドシートを確認してください。")
        return
    
    st.success(f"✅ {len(df)} 件のデータを読み込みました")
    
    # サイドバーでフィルタリングオプション
    st.sidebar.header("検索オプション")
    
    # 検索方法の選択
    search_method = st.sidebar.radio(
        "検索方法",
        ["キーワード検索", "列ごとに絞り込み"],
        help="全体を検索するか、特定の列で絞り込むかを選択"
    )
    
    filtered_df = df.copy()
    
    if search_method == "キーワード検索":
        # キーワード検索
        search_term = st.sidebar.text_input(
            "🔎 検索キーワード",
            placeholder="選手名、チーム、ポジションなど",
            help="すべての列を対象に検索します"
        )
        
        if search_term:
            # 各列を文字列に変換して検索
            mask = df.apply(
                lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
                axis=1
            )
            filtered_df = df[mask]
    
    else:  # 列ごとに絞り込み
        st.sidebar.subheader("列ごとの絞り込み")
        
        # 各列でフィルタリング
        for col in df.columns:
            unique_values = df[col].dropna().unique()
            if len(unique_values) > 0 and len(unique_values) <= 50:  # 選択肢が50以下の場合のみ
                selected_values = st.sidebar.multiselect(
                    f"{col}",
                    options=sorted(unique_values.astype(str)),
                    default=None,
                    key=f"filter_{col}"
                )
                if selected_values:
                    filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]
    
    # 結果表示
    st.subheader(f"検索結果: {len(filtered_df)} 件")
    
    if not filtered_df.empty:
        # 表示する列を選択
        col1, col2 = st.columns([3, 1])
        with col1:
            display_columns = st.multiselect(
                "表示する列を選択",
                options=list(df.columns),
                default=list(df.columns),
                key="display_columns"
            )
        with col2:
            st.write("")  # スペーサー
            st.write("")  # スペーサー
            if st.button("🔄 リセット", use_container_width=True):
                st.cache_data.clear()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        if display_columns:
            # データフレームを表示
            st.dataframe(
                filtered_df[display_columns],
                use_container_width=True,
                height=600
            )
            
            # CSVダウンロード
            csv = filtered_df[display_columns].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSV形式でダウンロード",
                data=csv,
                file_name=f"player_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # 統計情報
            with st.expander("📊 統計情報"):
                st.write("#### データの概要")
                st.write(filtered_df[display_columns].describe())
        else:
            st.warning("表示する列を少なくとも1つ選択してください。")
    else:
        st.info("検索条件に一致するデータが見つかりませんでした。")
    
    # 元のデータの概要
    with st.expander("ℹ️ データセット情報"):
        st.write("#### 全データの列一覧")
        col_info = pd.DataFrame({
            '列名': df.columns,
            'データ型': df.dtypes.astype(str),
            '非欠損値数': df.count(),
            'ユニーク値数': [df[col].nunique() for col in df.columns]
        })
        st.dataframe(col_info, use_container_width=True)

if __name__ == "__main__":
    main()
