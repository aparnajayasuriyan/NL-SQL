import json
import os
import sqlite3
import traceback

import pandas as pd
import streamlit as st
from ollama import Client

st.set_page_config(
    page_title="AI-Powered SQL Analytics Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <div style="text-align:center; padding: 0.5rem 0 0.25rem 0;">
        <h1 style="margin:0; font-size:3rem; font-weight:800; color:#1F4E79; letter-spacing:0.04em;">DataBridge</h1>
        <p style="margin:0.35rem 0 0 0; font-size:1.15rem; color:#4B5563; font-weight:600;">
            Democratizing Enterprise Data through Intelligent Natural Language Parsing
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Premium dark-blue slate custom styling injection
st.markdown("""
    <style>
        .main { background-color: #F8F9FA; }
        .stButton>button { border-radius: 8px; width: 100%; }
        .stTextInput>div>div>input { border-radius: 8px; }
        .reportview-container .main .block-container{ max-width: 1200px; }
        .sidebar .sidebar-content { background-color: #1F4E79; color: white; }
    </style>
""", unsafe_allow_html=True)

if "db_connected" not in st.session_state:
    st.session_state.db_connected = False
if "conn" not in st.session_state:
    st.session_state.conn = None
if "schema_info" not in st.session_state:
    st.session_state.schema_info = {}
if "query_history" not in st.session_state:
    st.session_state.query_history = []


def load_config_from_file():
    """Loads simple KEY=value settings from a local secrets file if present."""
    config_path = os.path.join(os.path.dirname(__file__), "secrets.env")
    values = {}

    if not os.path.exists(config_path):
        return values

    with open(config_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")

    return values


config_values = load_config_from_file()

if "ollama_api_key" not in st.session_state:
    st.session_state.ollama_api_key = os.getenv("OLLAMA_API_KEY", config_values.get("OLLAMA_API_KEY", ""))
if "ollama_endpoint" not in st.session_state:
    st.session_state.ollama_endpoint = os.getenv(
        "OLLAMA_ENDPOINT",
        config_values.get("OLLAMA_ENDPOINT", "https://ollama.com/"),
    )
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = os.getenv("OLLAMA_MODEL", config_values.get("OLLAMA_MODEL", "gemma3:27b"))


def create_mock_database():
    """Generates an in-memory SQLite database populated with larger synthetic e-commerce tables."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            signup_date DATE,
            loyalty_tier TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT,
            price REAL,
            stock_quantity INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE,
            total_amount REAL,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    loyalty_tiers = ["Bronze", "Silver", "Gold", "Platinum", "Regular"]
    first_names = [
        "Ava", "Liam", "Maya", "Noah", "Sophia", "Ethan", "Olivia", "Lucas", "Emma", "Mason",
        "Isabella", "James", "Charlotte", "Benjamin", "Amelia", "Elijah", "Harper", "Alexander", "Evelyn", "Henry",
        "Abigail", "Michael", "Emily", "Daniel", "Elizabeth", "Matthew", "Sofia", "Joseph", "Ella", "David",
        "Scarlett", "Samuel", "Grace", "Carter", "Chloe", "Owen", "Victoria", "Wyatt", "Riley", "John",
        "Aria", "Jack", "Aurora", "Leo", "Nora", "Luke", "Hazel", "Jayden", "Lily", "Dylan",
        "Zoe", "Isaac", "Stella", "Gabriel", "Hannah", "Julian", "Lucy", "Mateo", "Layla", "Anthony",
        "Paisley", "Hudson", "Naomi", "Nathan", "Elena", "Christopher", "Aubrey", "Andrew", "Claire", "Joshua",
        "Skylar", "Isaiah", "Willow", "Ryan", "Mila", "Nathaniel", "Bella", "Caleb", "Luna", "Adrian",
        "Savannah", "Thomas", "Camila", "Aaron", "Violet", "Isaac", "Ruby", "Charles", "Audrey", "Jonathan",
        "Penelope", "Justin", "Brooklyn", "Jose", "Leah", "Logan", "Alice", "Hunter", "Eva", "Christian"
    ]
    last_names = [
        "Anderson", "Bennett", "Carter", "Davis", "Edwards", "Foster", "Garcia", "Hughes", "Ingram", "Johnson",
        "Keller", "Lopez", "Mitchell", "Nelson", "Owens", "Parker", "Quinn", "Roberts", "Simmons", "Turner",
        "Underwood", "Vega", "Wright", "Xavier", "Young", "Zhang", "Adams", "Brooks", "Coleman", "Duncan",
        "Ellis", "Fisher", "Griffin", "Harrison", "Ibarra", "Jackson", "Kim", "Liu", "Morgan", "Nguyen",
        "Ortiz", "Perry", "Reyes", "Shaw", "Taylor", "Upton", "Vargas", "Walters", "Xu", "Yates", "Zimmerman"
    ]
    customers_data = []
    for customer_id in range(1, 121):
        signup_month = ((customer_id - 1) % 12) + 1
        signup_day = ((customer_id - 1) % 28) + 1
        tier = loyalty_tiers[(customer_id - 1) % len(loyalty_tiers)]
        first_name = first_names[(customer_id - 1) % len(first_names)]
        last_name = last_names[(customer_id - 1) % len(last_names)]
        customers_data.append(
            (
                customer_id,
                f"{first_name} {last_name}",
                f"{first_name.lower()}.{last_name.lower()}{customer_id % 100}@example.com",
                f"2025-{signup_month:02d}-{signup_day:02d}",
                tier,
            )
        )
    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers_data)

    categories = ["Electronics", "Furniture", "Home", "Accessories", "Office"]
    product_prefixes = [
        "Aurora", "Nimbus", "Vertex", "Lumen", "Crest", "Harbor", "Pioneer", "Northstar", "Horizon", "Summit",
        "Atlas", "Nova", "Orbit", "Terra", "Echo", "Flux", "Pine", "Cedar", "Stone", "Breeze"
    ]
    product_suffixes = [
        "Lite", "Pro", "Max", "Ultra", "Plus", "X", "Elite", "Studio", "Mini", "Flex"
    ]
    products_data = []
    for product_id in range(1, 121):
        category = categories[(product_id - 1) % len(categories)]
        price = round(19.99 + ((product_id * 13) % 480) + (product_id % 5) * 0.5, 2)
        stock_quantity = 10 + ((product_id * 17) % 200)
        prefix = product_prefixes[(product_id - 1) % len(product_prefixes)]
        suffix = product_suffixes[(product_id - 1) % len(product_suffixes)]
        product_name = f"{prefix} {suffix}"
        products_data.append(
            (
                product_id,
                product_name,
                category,
                price,
                stock_quantity,
            )
        )
    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products_data)

    statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    orders_data = []
    for order_index in range(1, 121):
        order_id = 3000 + order_index
        customer_id = ((order_index - 1) % 120) + 1
        order_month = ((order_index - 1) % 12) + 1
        order_day = ((order_index - 1) % 28) + 1
        total_amount = round(49.99 + ((order_index * 29) % 3000) + (order_index % 7) * 2.25, 2)
        status = statuses[(order_index - 1) % len(statuses)]
        orders_data.append((order_id, customer_id, f"2026-{order_month:02d}-{order_day:02d}", total_amount, status))
    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders_data)

    conn.commit()
    return conn

def fetch_database_schema(conn):
    """Inspects the connected database to extract catalog metadata and formatting string blueprints."""
    schema_dict = {}
    cursor = conn.cursor()
    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        # Fetch columns for each table
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        # Extract column name & data type
        schema_dict[table] = [f"{col[1]} ({col[2]})" for col in columns]
        
    return schema_dict

def format_schema_for_llm(schema_dict):
    """Constructs a clean textual context mapping of the schema structure for the LLM prompt context."""
    schema_str = "DATABASE SCHEMA METADATA:\n"
    for table, cols in schema_dict.items():
        schema_str += f"Table: {table}\nColumns: {', '.join(cols)}\n\n"
    return schema_str

def get_table_sample(conn, table_name, limit=20):
    """Return a sample DataFrame for the requested table."""
    query = f"SELECT * FROM {table_name} LIMIT {limit};"
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception:
        return None

def execute_sql_query(conn, sql_query):
    """Execute SQL safely and return a DataFrame for SELECT queries or a status message for others."""
    cursor = conn.cursor()
    cursor.execute(sql_query)

    if cursor.description is None:
        conn.commit()
        rowcount = cursor.rowcount
        if rowcount == -1:
            return None, "Query executed successfully."
        return None, f"Query executed successfully. {rowcount} rows affected."

    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    return df, None

def generate_sql_with_ollama(api_key, endpoint, model_name, schema_context, user_prompt, failed_sql=None, error_msg=None):
    """Uses the Ollama Python client to translate natural language into optimized SQL queries."""
    system_instruction = (
        "You are an expert SQL translator. Your job is to convert natural language queries into valid SQLite queries "
        "based strictly on the provided schema metadata. "
        "Rules:\n"
        "1. Output ONLY the raw SQL code. No markdown boxes, no backticks (```), and no formatting decorations.\n"
        "2. Ensure table names and column headers match the catalog exactly.\n"
        "3. Do not generate destructive commands (like DROP, INSERT, or DELETE)."
    )

    prompt = f"{schema_context}\nUser Request: {user_prompt}\n"

    if failed_sql and error_msg:
        prompt += (
            f"\nYour previous attempt generated this SQL:\n{failed_sql}\n"
            f"This resulted in the following error: {error_msg}\n"
            "Analyze the error, correct your logic, and output only the revised raw SQL."
        )

    try:
        client = Client(
            host=endpoint,
            headers={"Authorization": "Bearer " + api_key},
        )
        response = client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama API request failed: {exc}") from exc

    raw_response = response
    content = ""
    if isinstance(response, dict):
        if "message" in response:
            if isinstance(response["message"], dict):
                content = response["message"].get("content", "")
            else:
                content = str(response["message"])
        elif "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if isinstance(choice, dict) and "message" in choice:
                content = choice["message"].get("content", "")
            else:
                content = str(choice)
        else:
            content = str(response)
    elif hasattr(response, "message"):
        message = response.message
        if isinstance(message, dict):
            content = message.get("content", "")
        elif hasattr(message, "content"):
            content = message.content
        else:
            content = str(message)
    else:
        content = str(response)

    sql_query = content.strip().replace("```sql", "").replace("```", "")
    if not sql_query:
        raise RuntimeError(
            "Ollama returned empty SQL. Raw response:\n" + json.dumps(raw_response, default=str, indent=2)
        )

    return sql_query

tabs = st.tabs(["Settings", "Database", "Query"])

with tabs[0]:
    st.markdown("## 🔐 System Configuration")

    with st.form("ollama_config_form"):
        st.text_input(
            "Ollama API Key",
            key="ollama_api_key",
            type="password",
            help="Paste your Ollama cloud API key.",
        )
        st.text_input(
            "Ollama API Endpoint",
            key="ollama_endpoint",
            placeholder="http://localhost:11434",
            help="Base URL for your Ollama service (without /api suffix). Local: http://localhost:11434, Cloud: https://your-provider-url",
        )
        st.text_input(
            "Ollama Model",
            key="ollama_model",
            placeholder="e.g. gemma3:27b",
            help="Specify the model name exposed by your Ollama cloud service.",
        )
        submitted = st.form_submit_button("Save Configuration")

    if submitted:
        st.success("Configuration saved. You can now run your query.")

with tabs[1]:
    st.markdown("## 💾 Database Source")
    
    db_source_type = st.selectbox(
        "Select Database Type",
        ["Demo Mode (In-Memory SQLite)", "External SQLite (.db)"]
    )
    
    if db_source_type == "Demo Mode (In-Memory SQLite)":
        if st.button("🔌 Initialize Demo Catalog"):
            with st.spinner("Provisioning Mock Database..."):
                st.session_state.conn = create_mock_database()
                st.session_state.schema_info = fetch_database_schema(st.session_state.conn)
                st.session_state.db_connected = True
                st.success("Connected to in-memory E-commerce Database!")
    else:
        db_path = st.text_input("SQLite Database File Path", value="local_database.db")
        if st.button("🔌 Establish File Connection"):
            try:
                st.session_state.conn = sqlite3.connect(db_path, check_same_thread=False)
                st.session_state.schema_info = fetch_database_schema(st.session_state.conn)
                st.session_state.db_connected = True
                st.success("Successfully connected to local database!")
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")

    if st.session_state.db_connected:
        st.markdown("---")
        st.markdown("### 🗺️ Live Schema Explorer")
        for table, cols in st.session_state.schema_info.items():
            with st.expander(f"📋 Table: {table}"):
                for col in cols:
                    st.text(f"🔹 {col}")

        st.markdown("### 🗺️ Sample Table View")
        sample_table = st.selectbox(
            "Select a table to preview",
            list(st.session_state.schema_info.keys()),
            help="Choose a table to preview the top 20 rows.",
        )

        if sample_table:
            sample_df = get_table_sample(st.session_state.conn, sample_table)
            st.markdown(f"### 📌 Top 20 rows from `{sample_table}`")
            if sample_df is None:
                st.error("Unable to load a sample for this table.")
            elif sample_df.empty:
                st.warning("The selected table exists but contains no rows.")
            else:
                st.dataframe(sample_df, use_container_width=True)

with tabs[2]:
    if not st.session_state.db_connected:
        st.info("👈 Use the Database tab to configure and connect your database first.")
    else:
        st.markdown("### 💬 Ask Your Database a Question")
        user_query = st.text_input(
            "Type your question below:",
            placeholder="e.g., Show me the name and email of all customers in the Gold loyalty tier who signed up in 2025."
        )
        
        if st.button("🚀 Analyze and Query"):
            if not st.session_state.ollama_api_key:
                st.error("⚠️ Please configure your Ollama API Key in the settings tab.")
            elif not st.session_state.ollama_endpoint:
                st.error("⚠️ Please provide your Ollama API endpoint in the settings tab.")
            elif not st.session_state.ollama_model:
                st.error("⚠️ Please provide the Ollama model name in the settings tab.")
            elif not user_query:
                st.warning("Please type a question or scenario to execute.")
            else:
                schema_context = format_schema_for_llm(st.session_state.schema_info)
                
                with st.spinner("AI thinking... Parsing intention and composing optimized SQL..."):
                    try:
                        sql_query = generate_sql_with_ollama(
                            st.session_state.ollama_api_key,
                            st.session_state.ollama_endpoint,
                            st.session_state.ollama_model,
                            schema_context,
                            user_query,
                        )
                        
                        st.markdown("#### 🧾 Executed SQL:")
                        st.code(sql_query, language="sql")
                        
                        try:
                            results_df, status_message = execute_sql_query(st.session_state.conn, sql_query)

                            st.markdown("#### 📊 Query Results:")
                            if results_df is not None:
                                if results_df.empty:
                                    st.warning("Query completed successfully, but returned 0 rows matching those criteria.")
                                else:
                                    st.dataframe(results_df, use_container_width=True)
                            else:
                                st.info(status_message)

                            st.session_state.query_history.append({"user": user_query, "sql": sql_query})

                        except Exception as db_err:
                            st.warning("⚠️ Initial database execution failed. Attempting automatic query healing...")

                            corrected_sql = generate_sql_with_ollama(
                                st.session_state.ollama_api_key,
                                st.session_state.ollama_endpoint,
                                st.session_state.ollama_model,
                                schema_context,
                                user_query,
                                failed_sql=sql_query,
                                error_msg=str(db_err),
                            )

                            st.markdown("#### 🔧 Corrected execution strategy:")
                            st.code(corrected_sql, language="sql")
                            st.markdown("#### 🧾 Executed corrected SQL:")
                            st.code(corrected_sql, language="sql")

                            corrected_df, corrected_status = execute_sql_query(st.session_state.conn, corrected_sql)

                            st.markdown("#### 📊 Query Results:")
                            if corrected_df is not None:
                                if corrected_df.empty:
                                    st.warning("Healed query completed, but returned 0 data rows.")
                                else:
                                    st.dataframe(corrected_df, use_container_width=True)
                            else:
                                st.info(corrected_status)

                            st.session_state.query_history.append({"user": user_query, "sql": corrected_sql})
                            
                    except Exception as ex:
                        st.error("System failed to execute parsing flow. See debug tracking below:")
                        st.code(traceback.format_exc(), language="python")

if st.session_state.query_history:
    st.markdown("---")
    with st.expander("⏳ Session Audit Trail"):
        for idx, item in enumerate(reversed(st.session_state.query_history)):
            st.markdown(f"**Query {len(st.session_state.query_history) - idx}:** {item['user']}")
            st.code(item['sql'], language="sql")
            st.markdown("---")