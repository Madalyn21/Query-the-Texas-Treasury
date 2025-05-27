import openai

def generate_sql_from_nl(user_question: str) -> str:
    schema_description = """
Table: transactions
Columns:
- confidential: TEXT
- agency_number: INTEGER
- fund_number: INTEGER
- appropriation_number: INTEGER
- appropriation_year: INTEGER
- fiscal_year: INTEGER
- fiscal_month: INTEGER
- program_cost_account: INTEGER
- object_number: INTEGER
- vendor_number: TEXT
- mail_code: TEXT
- vendor_name: TEXT
- revision_indicator: TEXT
- amount_payed: TEXT (currency, like "$492.48")
- agency_title: TEXT
- appropriation_title: TEXT
- object_title: TEXT
- fund_title: TEXT
- agency_title_lower: TEXT
- id: INTEGER
"""

    prompt = f"""
You are an expert SQL generator. Given a user's question and the database schema, create an accurate SQL query.

Schema:
{schema_description}

User question:
\"\"\"{user_question}\"\"\"

SQL query:
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates SQL from natural language."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=200
    )

    sql = response["choices"][0]["message"]["content"].strip()
    if not sql.lower().startswith("select"):
        raise ValueError("Unsafe or invalid SQL generated.")
    return sql
