# SQL Database Chatbot with Intelligent Query Generation

A production-ready natural language interface to query your SQL Server 2005 database using advanced 3-stage intelligent query generation with LangChain and OpenAI.

## Features
- 🤖 **Ask questions in natural language** - No SQL knowledge required
- 🧠 **Intelligent 3-stage query generation**:
  1. Automatic table discovery with fuzzy matching
  2. Dynamic column name resolution
  3. Smart abbreviation handling (amount→amt, date→dt, etc.)
- 🔍 **Automatic SQL query generation** optimized for SQL Server 2005
- 💬 **Natural language responses** with context
- 📊 **Optional debug mode** - View SQL queries and raw results
- 🎨 **Beautiful Gradio web interface**
- ⚡ **Instant startup** - No metadata pre-loading
- 🛡️ **Comprehensive error handling** - User-friendly error messages
- 🏢 **Enterprise-ready** - Handles large databases with 100+ tables

## What Makes This Smart?

### Intelligent Table Discovery
- **Problem**: You have hundreds of tables with naming pattern `tbdw_tgt_*_fact` and `tbdw_tgt_*_dim`
- **Solution**: AI extracts keywords from your question and finds matching tables automatically
- **Example**: "real estate summary fact" → finds `tbdw_tgt_real_estate_summary_fact`

### Smart Column Mapping
- **Problem**: Users don't know exact column names (e.g., `loan_requested_amt`)
- **Solution**: AI discovers actual columns and maps natural language to database columns
- **Example**: "loan requested amount" → `loan_requested_amt`

### Common Abbreviations Handled
- amount → amt
- description → desc
- count → cnt
- indicator → ind
- date → dt
- datetime → dtm
- name → nm

## Setup

### Prerequisites
- Python 3.8+
- SQL Server 2005 (or newer)
- ODBC Driver for SQL Server
- OpenAI API key

### 1. Install Dependencies

**Using uv (Recommended):**
```bash
uv sync
```

**Or using pip:**
```bash
pip install -r requirements.txt
```

### 2. Configure Database Connection

Update `config.ini`:
```ini
[API]
OPENAI_API_KEY = your-openai-api-key-here

[DATABASE]
SERVER = your-server-name\instance
DATABASE = your-database-name
DRIVER = SQL Server
```

**Important**: For SQL Server 2005, use `DRIVER = SQL Server` (not "ODBC Driver 17")

### 3. Run the App

**Using uv:**
```bash
uv run app.py
```

**Or using Python:**
```bash
python app.py
```

The app will automatically open in your browser at: http://127.0.0.1:7860

## Running Tests

Install dependencies with `uv sync` (or `pip install -r requirements.txt`), then run:

```bash
uv run pytest
# or
pytest
```

The test suite uses lightweight fakes for the database and LLM so it runs without real network or database connections.

## Usage

1. **Enter your question** in plain English
2. **Optional:** Check "Show SQL query and raw results" for debugging
3. **Click "Ask Question"** or press Enter
4. **View the answer** in natural language

## Example Questions

### For Loan Data Warehouse
- "What is the max loan requested amount in the summary fact table?"
- "How many loans are there with closing date of 19870708?"
- "Show me the top 10 loan accounts by value"
- "What are the distinct lenders in the database?"

### General Queries
- "Show me the first 5 tables in the database"
- "How many records are in the loan account summary fact table?"
- "What is the average property market value?"

## Edge Cases Handled

The chatbot intelligently handles:

1. ✅ **Empty/whitespace questions** - Clear prompt to enter a question
2. ✅ **Invalid table names** - Suggests correct naming patterns
3. ✅ **Invalid column names** - Shows common abbreviations
4. ✅ **Date format mismatches** - Handles YYYYMMDD format (e.g., 19870708)
5. ✅ **Natural language variations** - Maps synonyms to actual columns
6. ✅ **API quota errors** - Clear instructions to add credits
7. ✅ **Database connection errors** - Diagnostic information
8. ✅ **No results found** - User-friendly message
9. ✅ **SQL syntax errors** - Helpful debugging tips

## Architecture

### 3-Stage Intelligent Query Generation

```
User Question
     ↓
┌────────────────────────────────────────┐
│  Stage 1: Table Discovery              │
│  - Extract keywords from question      │
│  - Search for matching tables using    │
│    INFORMATION_SCHEMA.TABLES           │
│  - Enforce tbdw_tgt_* naming pattern   │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│  Stage 2: Column Discovery             │
│  - Select best matching table          │
│  - Query INFORMATION_SCHEMA.COLUMNS    │
│  - Get actual column names             │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│  Stage 3: SQL Generation               │
│  - Map natural language to columns     │
│  - Handle abbreviations                │
│  - Generate SQL Server 2005 syntax     │
│  - Use dbo.table_name format           │
└────────────────────────────────────────┘
     ↓
  Execute Query → Natural Language Answer
```

### Key Optimizations

- **No metadata pre-loading**: Instant startup regardless of database size
- **Dynamic table discovery**: Queries tables on-demand
- **Custom data type handling**: Suppresses warnings for SQL Server 2005 custom types
- **SQL Server 2005 compatibility**: Uses `use_setinputsizes=False` for legacy driver

## Troubleshooting

### API Quota Error
**Error**: "Your OpenAI API key has insufficient credits"

**Solution**:
1. Visit https://platform.openai.com/account/billing
2. Add payment method and credits
3. Note: ChatGPT Plus ≠ API access (these are separate services)

### Database Connection Error
**Error**: "Couldn't connect to the database"

**Check**:
- SQL Server is running
- Connection details in `config.ini` are correct
- You have the correct ODBC driver installed
- Network/firewall allows connection

### Table Not Found Error
**Error**: "Invalid object name"

**Solution**:
- All tables follow pattern: `dbo.tbdw_tgt_*_fact` or `dbo.tbdw_tgt_*_dim`
- Try: "Show me the first 5 tables in the database" to see available tables
- Be more specific in your question

### Column Not Found Error
**Error**: "Invalid column name"

**Solution**:
- Enable "Show SQL query" to see what was attempted
- Remember common abbreviations: amount→amt, count→cnt, date→dt
- Try asking: "What columns are in the [table name] table?"

## File Structure

```
chat_with_sql_server/
├── app.py              # Main Gradio application with 3-stage intelligence
├── main.ipynb          # Jupyter notebook (development/testing)
├── config.ini          # Database and API configuration
├── requirements.txt    # Python dependencies
├── pyproject.toml      # UV project configuration
├── uv.lock             # UV lock file
├── run_app.bat         # Windows quick launcher
└── README.md           # This file
```

## Technologies Used

- **Gradio** - Modern web UI framework
- **LangChain** - LLM orchestration and chaining
- **OpenAI GPT-3.5-turbo** - Natural language understanding
- **SQL Server 2005** - Enterprise database
- **SQLAlchemy** - Database abstraction layer
- **pyodbc** - ODBC database connectivity
- **uv** - Fast Python package installer

## Advanced Configuration

### Switching to a Different LLM Model

Edit [app.py:202](app.py#L202):
```python
llm = ChatOpenAI(model="gpt-4")  # Use GPT-4 for better accuracy
```

### Limiting Result Size

Add `TOP` limit to protect against large queries:
```python
# In generate_smart_sql(), add a safety check
if "SELECT" in final_query and "TOP" not in final_query.upper():
    final_query = final_query.replace("SELECT", "SELECT TOP 1000", 1)
```

### Custom Table Patterns

If your database uses different naming conventions, update:
- [app.py:88-89](app.py#L88-L89) - Schema information
- [app.py:113-115](app.py#L113-L115) - Table naming patterns
- [app.py:126](app.py#L126) - Search pattern

## Security Considerations

- ⚠️ **Queries are plain text**: The LLM generates full SQL strings that are executed directly—no parameter binding or sanitization is performed.
- ✅ **API key storage**: Stored in local `config.ini` (add to .gitignore)
- ✅ **Read-only recommended**: Consider using a read-only database user
- ✅ **No direct user SQL**: All queries are AI-generated from natural language
- 🔒 **Hardening (recommended)**: Enforce table/column allowlists, add parameter binding where possible, and restrict the database user to least-privilege access.

## Performance

- **Startup time**: < 2 seconds (no metadata loading)
- **Query time**: 3-8 seconds (depends on API latency)
- **Stages**: 3 LLM calls per question (table discovery + column discovery + SQL generation)
- **Database queries**: 2-3 INFORMATION_SCHEMA queries + 1 final data query

## Future Enhancements

Potential improvements:
- [ ] Query result caching
- [ ] Query history with re-run capability
- [ ] Export results to CSV/Excel
- [ ] Multi-table JOIN support
- [ ] Aggregation intelligence (GROUP BY, HAVING)
- [ ] Fuzzy matching for typos
- [ ] Query performance optimization suggestions
- [ ] Support for stored procedures

## Contributing

To improve the chatbot:
1. Test with your specific database schema
2. Add more example questions to `gr.Examples`
3. Tune prompts in `template_find_tables`, `template_discover`, and `template`
4. Adjust error messages for your use case

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions:
- Check the troubleshooting section above
- Review error messages (they're designed to be helpful!)
- Enable "Show SQL query" mode to debug
- Verify your database naming follows `dbo.tbdw_tgt_*` pattern

---

**Built with ❤️ for enterprise SQL Server 2005 data warehouses**
