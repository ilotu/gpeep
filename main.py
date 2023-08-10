from datetime import datetime, timedelta
import json, time

import gspread, bbcode
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import streamlit_authenticator as stauth


def authenticate_users(config):
    credentials = dict(config['credentials'])
    cookie = dict(config['cookie'])
    preauthorized_emails = list(config['preauthorized']['emails'])

    authenticator = stauth.Authenticate(
        credentials,
        cookie['name'],
        cookie['key'],
        cookie['expiry_days'],
        preauthorized_emails
    )

    name, authentication_status, username = authenticator.login("Login", "main")
    role = config['credentials']['usernames'][username]['role']

    return authenticator, name, authentication_status, username, role

def connect_to_google_sheets(config):
    # Google Sheets 연동 설정
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    # JSON 문자열을 파이썬 딕셔너리로 변환
    creds_json = json.loads(config["google_service_account"]["creds_json"])

    # 서비스 계정 자격 증명 생성
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)

    return client

def load_spreadsheets(config, client):
    # 스프레드시트 열기
    sheet_ids_json = json.loads(config['spreadsheet_ids']['sheet_ids_json'])
    spreadsheet_name = st.sidebar.selectbox('문법 영역', sheet_ids_json.keys())
    spreadsheet = client.open_by_key(sheet_ids_json.get(spreadsheet_name))

    worksheet = spreadsheet.worksheet("문제") # 특정 워크시트 열기 (이름을 사용)
    rows = worksheet.get_all_records() # 데이터 읽기

    return worksheet, rows

def parse_ids_for_indexing(rows):
    # ID의 앞부분과 소분류 추출
    prefixes_with_subcategory = sorted(list(set([f"{row['ID'][:-4]} // {row['소분류']}" for row in rows if row['ID']])))

    # 사용자가 선택할 수 있는 접두어 및 소분류 목록
    selected_option = st.sidebar.selectbox('ID 및 소분류', prefixes_with_subcategory)
    selected_prefix, selected_subcategory = selected_option.split(" // ")

    # 해당 접두어와 일치하는 숫자 범위 찾기
    suffixes = [row['ID'][-3:] for row in rows if row['ID'].startswith(selected_prefix)]
    suffixes.sort()

    # suffixes 리스트를 세 자리 문자열 형식으로 변환
    suffixes_str = [str(suffix).zfill(3) for suffix in suffixes]

    # selected_suffix를 사용자가 선택하게 함
    selected_suffix = st.sidebar.number_input('문제 번호 (001 ~ ' + suffixes_str[-1] + ')', min_value=1, max_value=int(suffixes_str[-1]), value=1, step=1, format="%03d")

    # 선택된 ID에 해당하는 행 찾기
    selected_id = selected_prefix + '-' + str(selected_suffix).zfill(3)  # '-'를 추가해 접두어와 접미어를 결합
    selected_row = next((row for row in rows if row['ID'] == selected_id), None)

    return selected_row

def load_each_row(role):
    edit_data = {}
    types = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1-1', 'B1-2', 'B1-N', 'B2', 'B3', 'B4-1', 'B4-2', 'B4-N', 'C1', 'C2', 'C3', 'C4', 'C4-2', 'C5', 'D1', 'D1-2', 'D1', 'D1-N', 'D2-1', 'D2-2', 'D3', 'D4']
    directions = st.empty()
    st.text("")
    left_column, right_column = st.columns(2)

    if role == 'proofreader':
        directions.markdown("###### 🖊 검토 사항을 입력한 후 저장을 눌러 주세요.\n")

        if selected_row:
            for key, value in selected_row.items():
                if key in ['검토사항', '해설 검토사항']:
                    edit_data[key] = st.text_area(key.upper(), value, height=90, placeholder=f'{key}을 입력하세요.')

                elif key == 'ID':
                    left_column.markdown(f"<div class='text-input-label'>{key.upper()}</div>", unsafe_allow_html=True)
                    left_column.markdown(f"<div class='text-input-container'>{value}</div>", unsafe_allow_html=True)
                    left_column.markdown('\n')

                elif key == 'stage':
                    left_column.markdown(f"<div class='text-input-label'>{key.upper()}</div>", unsafe_allow_html=True)
                    left_column.markdown(f"<div class='text-input-container'>{value}</div>", unsafe_allow_html=True)
                    left_column.markdown('\n')

                elif key == '소분류':
                    right_column.markdown(f"<div class='text-input-label'>{key.upper()}</div>", unsafe_allow_html=True)
                    right_column.markdown(f"<div class='text-input-container'>{value}</div>", unsafe_allow_html=True)
                    right_column.markdown('\n')

                elif key == 'type':
                    right_column.markdown(f"<div class='text-input-label'>{key.upper()}</div>", unsafe_allow_html=True)
                    right_column.markdown(f"<div class='text-input-container'>{value}</div>", unsafe_allow_html=True)
                    right_column.markdown('\n')

                elif key and key not in ['stage', '중복']:
                    if 'picture' in key and '그림' not in selected_row['instructions']:
                        continue
                    st.markdown(f"<div class='text-input-label'>{key.upper()}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='text-input-container'>{bbcode.render_html(value)}</div>", unsafe_allow_html=True)
                    st.markdown('\n')
        else:
            st.error("선택된 ID의 행을 찾을 수 없습니다.")

    elif role == 'editor':
        directions.markdown("###### 🖊 수정 사항을 입력한 후 저장을 눌러 주세요.\n")

        if selected_row:
            for key, value in selected_row.items():
                if key == 'ID':
                    left_column.markdown(f"<div class='text-input-label'>{key.upper()}</div>", unsafe_allow_html=True)
                    left_column.markdown(f"<div class='text-input-container'>{value}</div>", unsafe_allow_html=True)
                    left_column.markdown('\n')

                elif key == 'stage':
                    edit_data[key] = left_column.number_input(key.upper(), min_value=1, max_value=4, value=value, step=1)

                elif key == '소분류':
                    edit_data[key] = right_column.text_input(key.upper(), value)

                elif key == 'type':
                    default_index = types.index(value) if value in types else -1
                    edit_data[key] = right_column.selectbox(key.upper(), types, index=default_index)

                elif key == 'e-passage':
                    edit_data[key] = st.text_area(key.upper(), value, height=90)

                elif key == 'solve':
                    edit_data[key] = st.text_area(key.upper(), value, height=90)
                    st.markdown(bbcode.render_html(f'{value}'), unsafe_allow_html=True)

                elif key == 'explanation':
                    edit_data[key] = st.text_area(key.upper(), value, height=150)
                    st.markdown(bbcode.render_html(f'{value}'), unsafe_allow_html=True)

                elif key == 'translation':
                    edit_data[key] = st.text_input(key.upper(), value)
                    st.markdown(bbcode.render_html(f'{value}'), unsafe_allow_html=True)

                elif key == '검토 날짜':
                    st.markdown(f"<div class='text-input-label'>{key.upper()}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='text-input-container'>{value}</div>", unsafe_allow_html=True)
                    st.markdown('\n')

                elif key and key not in ['소분류', 'stage', '중복', '검토사항', '해설 검토사항', '검토 날짜']:
                    if 'picture' in key and '그림' not in selected_row['instructions']:
                        continue
                    edit_data[key] = st.text_input(key.upper(), value)
        else:
            st.error("선택된 ID의 행을 찾을 수 없습니다.")

        return edit_data

def save_row(role, selected_row, edit_data):
    if role == 'proofreader':
        # 현재 날짜와 시간 가져오기
        review_date = f'검토: {(datetime.now() - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")} / {username}'

        # "검토 날짜" 열 이름으로 해당 열의 인덱스 찾기
        proofread_column_idx = list(selected_row.keys()).index('검토사항')+1
        proofread_explain_column_idx = list(selected_row.keys()).index('해설 검토사항')+1
        review_date_column_idx = list(selected_row.keys()).index('검토 날짜')+1

        # Google Sheets에 업데이트
        worksheet.update_cell(row_idx+2, proofread_column_idx, edit_data['검토사항'])
        worksheet.update_cell(row_idx+2, proofread_explain_column_idx, edit_data['해설 검토사항'])
        worksheet.update_cell(row_idx+2, review_date_column_idx, f'검토: {review_date} / {username}')

    elif role == 'editor':
        # 수정된 데이터를 리스트로 변환
        updated_row = [edit_data.get(key, value) for key, value in selected_row.items()]

        # 현재 날짜와 시간을 가져와서 포맷팅
        review_date = f'수정: {(datetime.now() - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")} / {username}'

        # "검토 날짜" 열 이름으로 해당 열의 인덱스 찾기
        review_date_column_idx = list(selected_row.keys()).index('검토 날짜')

        # 해당 열에 오늘 날짜와 시간을 삽입
        updated_row[review_date_column_idx] = review_date

        # Google Sheets에 업데이트
        worksheet.update('A' + str(row_idx + 2), [updated_row])

    st.sidebar.info(f"저장 완료 💾\n\nID: {selected_row.get('ID')}\n\n시간:{datetime.now().strftime('%I:%M:%S %p')}")

    time.sleep(0.3)
    st.experimental_rerun()


if __name__ == "__main__":
    st.set_page_config(
        page_title="Grammar PEEP 검수용 페이지",
        page_icon="📑",
        layout="centered",
        initial_sidebar_state="auto",
    )

    config = st.secrets
    authenticator, name, authentication_status, username, role = authenticate_users(config)

    if authentication_status == False:
        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    if authentication_status == None:
        st.warning("아이디와 비밀번호를 입력하세요.")

    if authentication_status:
        authenticator.logout("로그아웃", "sidebar")
        st.sidebar.title(f"{name} 님, 환영합니다. ({role})")

        client = connect_to_google_sheets(config)
        worksheet, rows = load_spreadsheets(config, client)
        selected_row = parse_ids_for_indexing(rows)

        # css 적용
        custom_css = """
        <style>
        @import url(//fonts.googleapis.com/earlyaccess/notosanskr.css);

        .css-nahz7x, .css-1qg05tj, .st-c8, .css-8ojfln, .css-7ym5gk, .st-af, .text-input-container {
            font-family: 'Noto Sans KR', sans-serif;
        }

        .css-nahz7x, .st-af, .st-c8 {
            font-size: 15px;
        }

        .css-8ojfln, .css-7ym5gk {
            font-size: 12px;
        }

        .css-1qg05tj {
            font-size: 10px;
        }

        .text-input-label {
            font-size: 14px;
        }

        .text-input-container {
            border: 1px dashed #DBDADA;
            border-radius: 5px;
            padding: 7px;
            margin: 3px 0;
            background-color: #FFFFFF;
            font-size: 15px;
        }
        </style>
        """
        st.markdown(custom_css, unsafe_allow_html=True)

        edit_data = load_each_row(role)

        # "저장" 버튼
        with st.sidebar:
            if st.sidebar.button('검토사항 저장 💾', help='저장을 눌러야 실제 데이터에 반영됩니다.'):
                with st.spinner(text="저장 중... 기다려 주세요 ⏳"):
                    row_idx = rows.index(selected_row) # 행 인덱스 찾기
                    save_row(role, selected_row, edit_data)

            # 새로고침 버튼
            if st.sidebar.button('새로고침'):
                with st.spinner(text="새로고침 중... 기다려 주세요 ⏳"):
                    time.sleep(0.3)
                    st.experimental_rerun()