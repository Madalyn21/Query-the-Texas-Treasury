import openai
import os
import re
def generate_sql_from_nl(user_question: str) -> str:
    openai.api_key = os.getenv("API_KEY")

    """Generate an SQL query from a natural language question using GPT-4."""

    schema_description = """
table_info = {
        "Payment Information": ("p", "paymentinformation", "p.vendor, p.vendor_number, p.agency, p.agency_number, p.dollar_value::numeric as dollar_value, p.fund_title, \
        p.fund_number, p.appropriation_year, p.fiscal_year, p.fiscal_month, p.appropriation_title, p.object_title, p.object_number, p.revision_indicator, \
        p.confidential, p.program_cost_account, p.mail_code"),
        "Contract Information": ("c", "contractinfo", "c.contract_id, c.vendor, c.vendorid_num, c.agency, c.dollar_value::numeric as dollar_value, c.subject, c.status, c.award_date, \
        c.completion_date, c.fiscal_year, c.fiscal_month, c.procurement_method, c.category, c.ngip_cnc")
    }
"""

    system_message = "You are an expert SQL assistant. Generate SQL queries based on natural language questions and a database schema."
    user_prompt = f"""
Given the following database schema and user question, generate a valid and safe SQL SELECT query that retrieves relevant information. If information on schema descriptions is not explicitly given, use best judgement.

Formatting Rule:
- Start the WHERE clause with `1=1` (e.g., `WHERE 1=1 AND p.fiscal_year = 24`).
- Use two-digit fiscal year formats only (e.g., 24 for 2024, 25 for 2025). Do not use four-digit years.
- When writing WHERE conditions, prefix all column names with `p.` (e.g., `p.fiscal_year = 24`, `p.agency = 'ABC'`).
- Do NOT use the `p.` prefix anywhere else in the query (e.g., not in SELECT, FROM, or GROUP BY clauses).
- Do not use escape sequences or \\n in the prompt, instead have it all out on one line.
- Use `AS p` to alias the main table in the FROM clause (e.g., `FROM transactions AS p`).

Example Output: SELECT * FROM paymentinformation WHERE p.fiscal_year BETWEEN 24 AND 25 AND p.agency = 'COURT OF CRIMINAL APPEALS')"

Schema:
{schema_description}

User Question:
\"\"\"{user_question}\"\"\"

SQL Query:
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            max_tokens=300
        )

        sql_text = response["choices"][0]["message"]["content"].strip()
        final_sql = re.sub(r"^```sql|```$", "", sql_text.strip(), flags=re.IGNORECASE).strip()
        if not final_sql.lower().startswith("select"):
            raise ValueError("Only SELECT queries are allowed. Generated query was:\n" + final_sql)


    # Basic safety check
        if not final_sql.lower().startswith("select"):
            raise ValueError("Only SELECT queries are allowed. Generated query was:\n" + final_sql)

        return final_sql

    except Exception as e:
        raise RuntimeError(f"Error generating SQL: {str(e)}")
