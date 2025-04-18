import streamlit as st
import sqlite3
import pandas as pd
import os
from utils.llm_wrapper_test import generate_sql_from_nl
from utils.get_db_info import (
    get_all_table_names,
    get_table_schema,
    get_table_statistics,
    plot_histograms,
    get_numerical_data,
)

# ---- Session State Initialization ----
if 'query_history' not in st.session_state:
    st.session_state.query_history = []

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Overview"

if 'user_query' not in st.session_state:
    st.session_state.user_query = ""
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = ""
if 'query_results' not in st.session_state:
    st.session_state.query_results = None
if 'refine_query' not in st.session_state:
    st.session_state.refine_query = False
if 'last_action' not in st.session_state:
    st.session_state.last_action = ""
if "db_path" not in st.session_state:
    st.session_state.db_path = "db/prototype.db"

db_path = st.session_state.db_path


def activate_refinement():
    st.session_state.refine_query = True

def reset_query():
    st.session_state.user_query = ""
    st.session_state.sql_query = ""
    st.session_state.query_results = None
    st.session_state.refine_query = False
    st.session_state.last_action = ""
    st.session_state.active_tab = "Query"
    st.rerun()

def update_query_history(sql_query, table_name, df):
    if st.session_state.query_history:
        last_item = st.session_state.query_history[-1]
        if last_item['table'] == table_name:
            last_item['query'] = sql_query
            last_item['results'] = df
            return

    st.session_state.query_history.append({
        'query': sql_query,
        'table': table_name,
        'results': df
    })

    st.session_state.query_history = st.session_state.query_history[-10:]

# ---- Sidebar UI ----
st.markdown("""
<style>
    section[data-testid="stSidebar"] { width: 525px !important; }
    section[data-testid="stSidebar"] > div:first-child { width: 520px !important; }
    .css-1d391kg, .css-1v0mbdj, .css-1cypcdb { font-size: 18px !important; }
    section[data-testid="stSidebar"] .block-container { padding-top: 2rem; padding-left: 1.5rem; }
    label[data-baseweb="radio"] > div { padding: 6px 10px; border-radius: 5px; }
    label[data-baseweb="radio"]:hover { background-color: #333333; }
    input[type="radio"]:checked + div { background-color: #ff4b4b33; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

tab = st.sidebar.radio("Navigation", ["Upload CSV", "Overview", "Query", "History"], key="active_tab")

with st.sidebar.expander("User Guide", expanded=False):
    st.markdown("""
    ### How to Use This App

    **1. Upload CSV**: Load your own data and convert it into a SQL database.

    **2. Overview**: View structure and stats of the database.

    **3. Query**: Ask questions in natural language.

    **4. History**: See your last 10 queries.
    """)

def wipe_all_tables(conn):
    cur = conn.cursor()
    # Drop every user‑created table (skip SQLite’s internal tables)
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    for (tbl,) in cur.fetchall():
        cur.execute(f'DROP TABLE IF EXISTS "{tbl}";')
    conn.commit()

# ---- TAB: Upload CSV ----
if tab == "Upload CSV":
    st.title("Upload Your CSV File")
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head(), use_container_width=True)

        table_name = st.text_input("Table Name", value="uploaded_table")

        if st.button("Save to SQLite"):
            # uses fixed file for uploaded data
            db_upload_path = "db/uploaded.db"
            os.makedirs("db", exist_ok=True)
            conn = sqlite3.connect(db_upload_path)

            # wipes all tables in the upload DB
            wipe_all_tables(conn)

            # write the freshly‑uploaded table
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            conn.close()

            # point the rest of the app to the (now clean) upload DB
            st.session_state.db_path = db_upload_path
            # clear history
            st.session_state.query_history = []

            st.success(f"Uploaded and saved as '{table_name}' in 'uploaded.db'")

# ---- TAB: Overview ----
elif tab == "Overview":
    st.title("Database Overview")
    conn = sqlite3.connect(db_path)
    table_names = get_all_table_names(db_path)
    for table in table_names:
        st.header(f"Table: {table}")
        df_schema = pd.DataFrame(get_table_schema(conn, table))
        st.subheader("Schema")
        st.dataframe(df_schema, use_container_width=True)

        df_stats = pd.DataFrame(get_table_statistics(conn, table))
        st.subheader("Statistics")
        st.dataframe(df_stats, use_container_width=True)
    numerical_data = get_numerical_data(db_path)
    if numerical_data:
        st.header("Distributions")
        plot_histograms(numerical_data)
    else:
        st.info("No numerical data found.")
    conn.close()

# ---- TAB: Query ----
elif tab == "Query":
    st.title("Natural Language to SQL")
    user_question = st.text_input("Ask your question:", value=st.session_state.user_query)

    if st.button("Run Query") and user_question and st.session_state.last_action == "":
        with st.spinner("Generating SQL..."):
            try:
                sql_query, table_name = generate_sql_from_nl(user_question, db_path=db_path)
                if not sql_query:
                    st.warning("Model did not return SQL.")
                else:
                    st.session_state.user_query = user_question
                    st.session_state.sql_query = sql_query
                    conn = sqlite3.connect(db_path)
                    df = pd.read_sql_query(sql_query, conn)
                    conn.close()
                    st.session_state.query_results = df
                    update_query_history(sql_query, table_name, df)
                    st.session_state.last_action = "initial"
                    st.rerun()
            except Exception as e:
                st.error("Error running query")
                st.exception(e)

    if st.session_state.refine_query:
        refinement = st.text_area("Refinement:", height=100)
        if st.button("Submit Refinement"):
            if refinement:
                refined_prompt = f"Original query: {st.session_state.user_query}. Refinement: {refinement}"
                with st.spinner("Generating refined SQL..."):
                    try:
                        sql_query, table_name = generate_sql_from_nl(refined_prompt, db_path=db_path)
                        if sql_query:
                            st.session_state.sql_query = sql_query
                            conn = sqlite3.connect(db_path)
                            df = pd.read_sql_query(sql_query, conn)
                            conn.close()
                            st.session_state.query_results = df
                            update_query_history(sql_query, table_name, df)
                            st.session_state.refine_query = False
                            st.session_state.last_action = "refined"
                            st.rerun()
                    except Exception as e:
                        st.error("Refinement failed")
                        st.exception(e)
            else:
                st.warning("Please enter your refinement.")

    if st.session_state.sql_query:
        st.subheader("SQL Query")
        st.code(st.session_state.sql_query, language="sql")

    if st.session_state.query_results is not None:
        st.subheader("Query Results")
        st.dataframe(st.session_state.query_results, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            csv = st.session_state.query_results.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "query_results.csv", "text/csv")
        with col2:
            st.button("Refine Query", on_click=activate_refinement)
    st.markdown("---")
    st.button("Reset Query", on_click=reset_query)

# ---- TAB: History ----
elif tab == "History":
    st.title("Query History")
    if not st.session_state.query_history:
        st.info("No queries yet.")
    else:
        for i, item in enumerate(st.session_state.query_history, 1):
            with st.expander(f"Query {i}: {item['table']}"):
                st.code(item['query'], language='sql')
                st.dataframe(item['results'], use_container_width=True)
