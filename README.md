# Natural Language to SQL Explorer

A Streamlit web application that allows users to upload CSV data, explore the database, and query it using **natural language**. SQL queries are generated using a language model (via Cohere API), executed on an SQLite database, and results are displayed interactively.

Available using the following link: <br>
https://db-generic-nlp-sql-translate.streamlit.app
---

## Features

### Upload CSV

- Upload your own CSV file.
- Automatically converts it into a SQLite table.
- Replaces any previously uploaded tables.

### Database Overview

- View schema (column names, types) and basic statistics of each table.
- Visualize numerical data distributions with histograms.

### Natural Language Querying

- Ask questions in plain English.
- Backend LLM (Cohere) generates and runs the corresponding SQL query.
- View the SQL statement and resulting data.
- Option to refine queries interactively.
- Download results as CSV.

### Query History

- Access your 10 most recent queries.
- View SQL and results for each.

---

## How It Works

The app is primarily powered by:

- **Streamlit** for the user interface.
- **SQLite** for local data storage and querying.
- **Cohere** via the `cohere` Python SDK for generating SQL queries from natural language.
- **Matplotlib** for histogram plotting.
- **Pandas** for data manipulation.

The core files include:

- `app.py`: Main Streamlit application.
- `utils/llm_wrapper_test.py`: Handles NL-to-SQL generation via the Cohere API.
- `utils/get_db_info.py`: Retrieves table names, schemas, statistics, and plots from the SQLite DB.

---

## Requirements

Install dependencies using:

```bash
pip install -r requirements.txt
