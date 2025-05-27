import openai
import os
def generate_sql_from_nl(user_question: str) -> str:
    openai.api_key = os.getenv("API_KEY")

    """Generate an SQL query from a natural language question using GPT-4."""

    schema_description = """
Table: transactions
Columns:
p.vendor, p.vendor_number, p.agency, p.agency_number, p.dollar_value::numeric as dollar_value, p.fund_title, p.fund_number, p.appropriation_year, p.fiscal_year, p.fiscal_month, p.appropriation_title, p.object_title, p.object_number, p.revision_indicator,         p.confidential, p.program_cost_account, p.mail_code
"""

    system_message = "You are an expert SQL assistant. Generate SQL queries based on natural language questions and a database schema."
    user_prompt = f"""
Given the following database schema and user question, generate a valid and safe SQL SELECT query that retrieves relevant information. If information on schema descriptions is not explicitly given, use best judgement"

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

        # Extract the first SQL-like block, just in case
        lines = sql_text.splitlines()
        code_lines = [line for line in lines if line.strip()]
        if code_lines[0].lower().startswith("sql"):
            code_lines = code_lines[1:]

        final_sql = "\n".join(code_lines).strip()

        # Basic safety check
        if not final_sql.lower().startswith("select"):
            raise ValueError("Only SELECT queries are allowed. Generated query was:\n" + final_sql)

        return final_sql

    except Exception as e:
        raise RuntimeError(f"Error generating SQL: {str(e)}")
