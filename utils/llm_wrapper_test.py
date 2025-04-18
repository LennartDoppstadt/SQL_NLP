import cohere
import json
import sqlparse
import sqlite3
import streamlit as st

# Load the API key from secrets:
COHERE_API_KEY = st.secrets["COHERE_API_KEY"]
co = cohere.ClientV2(COHERE_API_KEY)

def generate_schema_prompt_from_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    schema_sql = []
    for (table,) in tables:
        cursor.execute(f"PRAGMA table_info('{table}');")
        columns = cursor.fetchall()
        column_defs = [f'"{col[1]}" {col[2]}' for col in columns]
        schema = f'CREATE TABLE IF NOT EXISTS "{table}" (\n    {", ".join(column_defs)}\n);'
        schema_sql.append(schema)

    conn.close()
    return "\n\n".join(schema_sql)


def get_system_prompt(db_path):
    schema = generate_schema_prompt_from_db(db_path)
    return {
        'role': 'system',
        'content': f"""
        You are an expert data analyst who writes clean, executable SQLite queries based on a given database schema and user request. Additionally, identify the primary table involved in the query.

        ## Rules:
        - Respond with a JSON object containing:
            - "sql_query": the valid SQL string
            - "table_name": a suitable name for the result table (capitalize each word)
        - Use only SELECT statements.
        - Do NOT include commentary.
        - Use only tables/columns from the schema below.

        ## Database schema:
        {schema}
        """
    }


def generate_sql_from_nl(user_query: str, db_path: str):
    try:
        system_prompt = get_system_prompt(db_path)
        response = co.chat(
            model="command-r-plus",
            messages=[system_prompt, {"role": "user", "content": user_query}],
            response_format={"type": "json_object"}
        )

        content = response.message.content[0].text.strip()
        result = json.loads(content)

        sql_query = sqlparse.format(result.get("sql_query", ""), reindent=True, keyword_case='upper')
        table_name = result.get("table_name", "Unknown")
        return sql_query, table_name
    except Exception as e:
        st.error("Failed to generate or parse SQL.")
        st.exception(e)
        return "", ""

