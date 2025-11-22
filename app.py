import os
import configparser
import gradio as gr
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from urllib.parse import quote_plus

# Read configuration from .ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Get the API key from the .ini file
try:
    openai_api_key = config['API']['OPENAI_API_KEY']
    os.environ['OPENAI_API_KEY'] = openai_api_key
    print("[OK] OpenAI API key loaded successfully from config.ini")
except KeyError:
    print("[WARNING] OPENAI_API_KEY not found in config.ini")

# Read database configuration from .ini file
server = config['DATABASE']['SERVER']
database = config['DATABASE']['DATABASE']
driver = config['DATABASE']['DRIVER']

# Connect to SQL Server
connection_string = f'DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes'
mssql_uri = f'mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}'

print(f"Connecting to database: {database} on server: {server}")
from sqlalchemy import create_engine, text
import warnings

# Suppress SQLAlchemy warnings for custom SQL Server 2005 data types
from sqlalchemy.exc import SAWarning
warnings.filterwarnings('ignore', category=SAWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='sqlalchemy')

# Create engine with optimizations for SQL Server 2005
engine = create_engine(
    mssql_uri,
    use_setinputsizes=False
)

# Create a simple database wrapper that doesn't load metadata
class SimpleDatabaseWrapper:
    """Lightweight database wrapper that executes queries without loading metadata"""
    def __init__(self, engine):
        self.engine = engine

    def run(self, query):
        """Execute a SQL query and return results as a string"""
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            if result.returns_rows:
                # Fetch all rows and format as string
                rows = result.fetchall()
                if not rows:
                    return "No results found."
                # Return formatted results
                return str([tuple(row) for row in rows])
            else:
                return f"Query executed successfully. Rows affected: {result.rowcount}"

    def get_table_info(self):
        """Returns empty string since we don't pre-load tables"""
        return ""

db = SimpleDatabaseWrapper(engine)
print("[OK] Connected successfully! Tables will be queried dynamically at runtime.")

# Setup LangChain components
def get_schema(inputs):
    """
    Dynamically get schema information based on the question.
    This queries the database at runtime instead of pre-loading all tables.
    """
    question = inputs.get("question", "") if isinstance(inputs, dict) else ""

    # Return a helpful message about querying the database dynamically
    schema_info = """
Available Database: CMWDW_Insurance on SQL Server 2005

IMPORTANT Table Naming Conventions:
- All tables use the 'dbo' schema prefix (e.g., dbo.table_name)
- Fact tables follow pattern: dbo.tbdw_tgt_*_fact (e.g., dbo.tbdw_tgt_loan_account_summary_fact)
- Dimension tables follow pattern: dbo.tbdw_tgt_*_dim (e.g., dbo.tbdw_tgt_loan_account_dim)
- NEVER use database.table format (e.g., CMWDW_Insurance.table_name is WRONG)
- ALWAYS use schema.table format (e.g., dbo.table_name is CORRECT)

To discover tables, use:
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_NAME LIKE 'tbdw_tgt_%'

To find columns in a table:
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'your_table_name'

SQL Server 2005 syntax:
- Use TOP instead of LIMIT (e.g., SELECT TOP 5 * FROM dbo.table_name)
- Use GETDATE() instead of NOW()
- Use LEN() instead of LENGTH()
"""
    return schema_info

# SQL generation prompt - Three stages for intelligent table and column discovery
template_find_tables = """You are a SQL expert working with a Microsoft SQL Server 2005 database named CMWDW_Insurance.

The user asked: "{question}"

Your task: Find relevant tables that match the user's question.

CRITICAL - Table Naming Convention:
- ALL fact tables follow pattern: tbdw_tgt_*_fact (with tbdw_tgt_ prefix)
- ALL dimension tables follow pattern: tbdw_tgt_*_dim (with tbdw_tgt_ prefix)

Examples:
- "loan account summary fact" → tbdw_tgt_loan_account_summary_fact
- "real estate summary fact" → tbdw_tgt_real_estate_summary_fact
- "property dimension" → tbdw_tgt_property_dim
- "lender dimension" → tbdw_tgt_lender_dim

Extract keywords from the user's question and search for matching tables:
1. Identify if they're asking about a fact table (summary, transaction, fact) or dimension (lookup, dimension, dim)
2. Extract key subject words (loan, property, real estate, customer, etc.)
3. Search using LIKE pattern with tbdw_tgt_% prefix

Write a SQL query to find matching tables. Use wildcards to find tables containing the keywords:

SQL Query:"""

template_discover = """You are a SQL expert working with a Microsoft SQL Server 2005 database named CMWDW_Insurance.

User Question: "{question}"

Available Tables Found:
{found_tables}

Your task: Select the BEST matching table and get its columns.

Instructions:
1. Choose the most relevant table from the list above
2. The table name will start with 'tbdw_tgt_'
3. Query to get ALL columns from that specific table

Write a SQL query to get the column names:
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'exact_table_name_from_above'

SQL Query:"""

template = """You are a SQL expert working with a Microsoft SQL Server 2005 database named CMWDW_Insurance.

User Question: {question}

Selected Table: {selected_table}

Available Columns:
{discovered_columns}

CRITICAL RULES:
1. Table Naming: ALWAYS use dbo.table_name format
   ✓ CORRECT: SELECT * FROM dbo.{selected_table}
   ✗ WRONG: SELECT * FROM CMWDW_Insurance.real_estate_summary_fact

2. Column Matching:
   - Match natural language to actual column names
   - Common abbreviations: amt=amount, desc=description, cnt=count, ind=indicator, dt=date, dtm=datetime, nm=name
   - Users may say "amount" but column is "amt"
   - Users may say "date" but column might be "dt" or "dtm"

3. Date Handling:
   - Dates like "19870708" are in YYYYMMDD format
   - Convert dates properly: WHERE date_column = '19870708' or CONVERT(VARCHAR(8), date_column, 112) = '19870708'
   - Handle different date formats in the data

4. SQL Server 2005 Syntax:
   - Use TOP not LIMIT
   - Use GETDATE() not NOW()
   - Use LEN() not LENGTH()
   - Use CONVERT for date/type conversions

Based on the question and available columns, write the SQL query.
Use ONLY columns from the list above and the table name: dbo.{selected_table}

SQL Query:"""

prompt_find_tables = ChatPromptTemplate.from_template(template_find_tables)
prompt_discover = ChatPromptTemplate.from_template(template_discover)
prompt = ChatPromptTemplate.from_template(template)

# Response generation prompt
template_response = """Based on the table schema below, question, sql query, and sql response, write a natural language response:
{schema}

Question: {question}
SQL Query: {query}
SQL Response: {response}
Answer:"""
prompt_response = ChatPromptTemplate.from_template(template_response)

# Initialize LLM
llm = ChatOpenAI(model="gpt-3.5-turbo")

# Chain to find tables
find_tables_chain = (
    prompt_find_tables
    | llm.bind(stop=["\nSQLResult:"])
    | StrOutputParser()
)

# Chain to discover columns
discovery_chain = (
    prompt_discover
    | llm.bind(stop=["\nSQLResult:"])
    | StrOutputParser()
)

# Query execution function
def run_query(query):
    return db.run(query)

# Three-stage intelligent SQL generation function
def generate_smart_sql(question):
    """
    Three-stage SQL generation:
    1. Find relevant tables matching the question
    2. Select best table and get its column names
    3. Generate the final SQL query using actual table and column names
    """
    try:
        # Stage 1: Find matching tables
        find_tables_query = find_tables_chain.invoke({"question": question})
        found_tables_result = db.run(find_tables_query.strip())

        # Stage 2: Discover columns from the best matching table
        discovery_query = discovery_chain.invoke({
            "question": question,
            "found_tables": found_tables_result
        })
        column_result = db.run(discovery_query.strip())

        # Extract table name from the discovery query
        # The query should be like: SELECT COLUMN_NAME FROM ... WHERE TABLE_NAME = 'table_name'
        import re
        table_match = re.search(r"TABLE_NAME\s*=\s*'([^']+)'", discovery_query, re.IGNORECASE)
        selected_table = table_match.group(1) if table_match else "unknown_table"

        # Stage 3: Generate final SQL with discovered columns and table
        final_query = (
            prompt
            | llm.bind(stop=["\nSQLResult:"])
            | StrOutputParser()
        ).invoke({
            "question": question,
            "selected_table": selected_table,
            "discovered_columns": column_result
        })

        return final_query.strip()
    except Exception:
        # Fallback: Return error message for debugging
        try:
            # Simple fallback
            return (
                RunnablePassthrough.assign(schema=get_schema)
                | prompt
                | llm.bind(stop=["\nSQLResult:"])
                | StrOutputParser()
            ).invoke({
                "question": question,
                "selected_table": "tbdw_tgt_unknown",
                "discovered_columns": "Unable to discover columns"
            })
        except:
            return f"SELECT 'Error: Unable to generate query for: {question}' AS error_message"

# Gradio interface function
def ask_database(question, show_details=False):
    """
    Process a natural language question about the database

    Handles edge cases:
    - Empty/whitespace questions
    - Invalid table names
    - Invalid column names
    - Date format mismatches
    - SQL syntax errors
    - API quota errors
    - Database connection errors

    Args:
        question: User's question in natural language
        show_details: Whether to show SQL query and raw results

    Returns:
        Formatted response with answer and optional details
    """
    # Edge Case 1: Empty question
    if not question.strip():
        return "Please enter a question."

    try:
        # Stage 1-3: Generate SQL query using intelligent 3-stage discovery
        sql_query = generate_smart_sql(question)

        # Edge Case 2: Check if query generation failed
        if "Error:" in sql_query or not sql_query.strip():
            return f"❌ **Unable to generate query**\n\nI couldn't understand your question. Please try:\n- Being more specific about table names\n- Using keywords like 'fact table' or 'dimension table'\n- Checking your spelling"

        # Stage 4: Execute the query to get raw results
        raw_result = db.run(sql_query)

        # Edge Case 3: Check for error results
        if "No results found" in str(raw_result):
            details = ""
            if show_details:
                details = f"### 🔍 Generated SQL Query\n```sql\n{sql_query.strip()}\n```"
            return f"### 💬 Answer\n\nNo data found matching your criteria.\n\n{details}"

        # Stage 5: Generate natural language answer
        answer = (
            prompt_response
            | llm
            | StrOutputParser()
        ).invoke({
            "schema": get_schema({"question": question}),
            "question": question,
            "query": sql_query,
            "response": raw_result
        })

        # Build response
        response = f"### 💬 Answer\n{answer}\n"

        if show_details:
            response += f"\n### 🔍 Generated SQL Query\n```sql\n{sql_query.strip()}\n```\n"
            response += f"\n### 📋 Raw Database Result\n```\n{raw_result}\n```"

        return response

    except Exception as e:
        error_str = str(e)

        # Edge Case 4: API quota errors
        if "429" in error_str or "quota" in error_str.lower():
            return "❌ **API Quota Error**\n\nYour OpenAI API key has insufficient credits.\n\n**To fix:**\n1. Visit https://platform.openai.com/account/billing\n2. Add payment method and credits\n\n**Note:** ChatGPT Plus ≠ API access (separate services)"

        # Edge Case 5: Invalid object name (table doesn't exist)
        elif "Invalid object name" in error_str or "42S02" in error_str:
            return f"❌ **Table Not Found**\n\nThe table doesn't exist in the database.\n\n**Tip:** All tables follow the pattern:\n- Fact tables: `dbo.tbdw_tgt_*_fact`\n- Dimension tables: `dbo.tbdw_tgt_*_dim`\n\n**Try:** 'Show me the first 5 tables in the database'"

        # Edge Case 6: Invalid column name
        elif "Invalid column name" in error_str or "42S22" in error_str:
            return f"❌ **Column Not Found**\n\nThe column doesn't exist in that table.\n\n**Tip:** Enable 'Show SQL query' to see what was attempted.\n\n**Common abbreviations:**\n- amount → amt\n- description → desc\n- count → cnt\n- date → dt or dtm"

        # Edge Case 7: Connection errors
        elif "connection" in error_str.lower() or "timeout" in error_str.lower():
            return "❌ **Database Connection Error**\n\nCouldn't connect to the database.\n\n**Possible causes:**\n- Database server is down\n- Network issues\n- Credentials expired"

        # Edge Case 8: Generic SQL errors
        else:
            return f"❌ **Error:** {error_str}\n\n**Tip:** Try enabling 'Show SQL query and raw results' to debug."

# Create Gradio interface
with gr.Blocks(title="SQL Database Chatbot", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🤖 SQL Database Chatbot
        Ask questions about your database in natural language!

        **Database:** {database} | **Server:** {server}
        """.format(database=database, server=server)
    )

    with gr.Row():
        with gr.Column(scale=2):
            question_input = gr.Textbox(
                label="💭 Your Question",
                placeholder="e.g., How many albums are in the database?",
                lines=2
            )

            show_details = gr.Checkbox(
                label="Show SQL query and raw results",
                value=False
            )

            submit_btn = gr.Button("🔍 Ask Question", variant="primary", size="lg")

    with gr.Row():
        output = gr.Markdown(label="Response")

    # Example questions
    gr.Examples(
        examples=[
            ["Show me the first 5 tables in the database"],
            ["How many loan accounts are in the summary fact table?"],
            ["What are the top 10 loan accounts by value?"]
        ],
        inputs=question_input
    )

    # Button click event
    submit_btn.click(
        fn=ask_database,
        inputs=[question_input, show_details],
        outputs=output
    )

    # Also allow Enter key to submit
    question_input.submit(
        fn=ask_database,
        inputs=[question_input, show_details],
        outputs=output
    )

    gr.Markdown(
        """
        ---
        ### 📝 Tips:
        - Ask questions in plain English
        - Check "Show SQL query" to see the generated SQL
        - Try the example questions to get started
        """
    )

# Launch the app
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting SQL Database Chatbot...")
    print("="*60)
    demo.launch(
        share=False,  # Set to True to create a public link
        server_name="127.0.0.1",
        server_port=None,  # Auto-find available port
        inbrowser=True  # Automatically open in browser
    )
