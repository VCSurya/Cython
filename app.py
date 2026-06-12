from flask import Flask, jsonify,request,send_file
from google import genai
import json
from hdbcli import dbapi
from flask_cors import CORS 
from openai import OpenAI
from io import BytesIO
import pandas as pd
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"]
)

SQL = None

client = OpenAI(api_key=str(os.getenv("OPENAI_API_KEY")))


def call_llm_get_sql(user_query):
    try:
        with open('prompt.txt','r') as file:
            prompt_text = file.read()
        client = genai.Client(api_key="AIzaSyCTgG5NzuNzPOM5r63lFe7yBy6jCmNfqrc")

        prompt = prompt_text + f"""
        << {user_query} >>
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        config={
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "SQL": {"type": "string"},
                        "status": {"type": "boolean"}
                    },
                    "required": ["SQL","status"]
                }
            }
        )

        data = json.loads(response.text)
        return {'success':True, "data":data}

    except Exception as e:
        return {'success':False, "error":str(e)}

def call_llm_get_reply(user_question,sql_query,sql_result):

        try:
            with open('study.txt','r') as file:
                prompt_text = file.read()
            client = genai.Client(api_key="AIzaSyCTgG5NzuNzPOM5r63lFe7yBy6jCmNfqrc")

            prompt = prompt_text + f"""
                        Input:

                        User Question:
                        {user_question}

                        SQL Query:
                        {sql_query}

                        SQL Result:
                        {sql_result}

                        Output:
                        Generate a professional, user-friendly response that answers the user's question based solely on the provided data.
                    """

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            return {'success':True, "reply":response.text}

        except Exception as e:
            return {'success':False, "error":str(e)}

def hana_db_sql_execution(sql_query):

    try:
        global SQL
        SQL = sql_query
        conn = dbapi.connect(
            address="dfad9e20-c1a8-44ea-80d7-930deb0901d7.hna1.prod-us10.hanacloud.ondemand.com",
            port=443,
            user="3890AB796E4C4CCA90D89ADB5045E72D_BT1U8IAY0FLCPSBUHLS1COWXD_RT",
            password="{~5=Zs&(z6)D_RO*0l p?^#t1Mb9 =N4G=X<lEpEsiR?w0PNfaf~F25zXM)MTQ;[;mPHPeaXxubP=Nq8%#,_F-SI(Eewc@G3o|WG&PTVf0z3]=l!6V%F(FAW11kuP~c#",
            encrypt=True,
            sslValidateCertificate=False
        )
        
        cursor = conn.cursor()
        cursor.execute(sql_query)

        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        # Header
        table_text = "| " + " | ".join(columns) + " |\n"
        table_text += "".join(["-------------"] * len(columns)) + "\n"

        # Data rows
        for row in rows:
            table_text += "| " + " | ".join(str(v) if v is not None else "" for v in row) + " |\n"

        return {'success':True,'result':table_text}

    except Exception as e:
        return {'success':False,'error':str(e)}

    finally:
        cursor.close()
        conn.close()

def call_openai_get_sql(user_query):
    try:
        with open('prompt.txt', 'r') as file:
            prompt_text = file.read()

        prompt = prompt_text + f"""
        << {user_query} >>
        
        Respond with valid JSON containing exactly these fields:
        - "SQL": the generated SQL query (string)
        - "status": whether the query is valid (boolean)
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sql_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "SQL": {"type": "string"},
                            "status": {"type": "boolean"}
                        },
                        "required": ["SQL", "status"],
                        "additionalProperties": False
                    }
                }
            },
            temperature=1  # Required for JSON schema mode
        )

        data = json.loads(response.choices[0].message.content)
        return {'success': True, "data": data}

    except json.JSONDecodeError as e:
        return {'success': False, "error": f"Invalid JSON response: {str(e)}"}
    except Exception as e:
        return {'success': False, "error": str(e)}

def call_openai_get_reply(user_question, sql_query, sql_result):
    """
    Generate a professional user-friendly response using OpenAI GPT-4o mini.
    Based on user question, SQL query, and SQL results.
    """
    try:


        with open('study.txt', 'r') as file:
            prompt_text = file.read()

        prompt = prompt_text + f"""Input:

User Question:
{user_question}

SQL Query:
{sql_query}

SQL Result:
{sql_result}

Output:
Generate a professional, user-friendly response that answers the user's question based solely on the provided data."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7
        )

        reply_text = response.choices[0].message.content
        return {'success': True, "reply": reply_text}

    except Exception as e:
        return {'success': False, "error": str(e)}

def classify_user_question(user_question):
    try:
        with open('classify.txt', 'r') as file:
            prompt_text = file.read()

        prompt = prompt_text + f"""
        USER QUESTION:
        << {user_question} >>
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "classify_user_question",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "msg": {"type": "string"},
                            "status": {"type": "boolean"}
                        },
                        "required": ["msg", "status"],
                        "additionalProperties": False
                    }
                }
            },
            temperature=1  # Required for JSON schema mode
        )

        data = json.loads(response.choices[0].message.content)
        return data
    except json.JSONDecodeError as e:
        return {'success': False, "error": f"Invalid JSON response: {str(e)}"}
    except Exception as e:
        return {'success': False, "error": str(e)}

@app.route('/export-excel')
def export_excel():

        global SQL
        
        if not SQL:
            return jsonify({"reply": "Something went wrong. Please raise a question first."})

        conn = dbapi.connect(
                    address="dfad9e20-c1a8-44ea-80d7-930deb0901d7.hna1.prod-us10.hanacloud.ondemand.com",
                    port=443,
                    user="3890AB796E4C4CCA90D89ADB5045E72D_BT1U8IAY0FLCPSBUHLS1COWXD_RT",
                    password="{~5=Zs&(z6)D_RO*0l p?^#t1Mb9 =N4G=X<lEpEsiR?w0PNfaf~F25zXM)MTQ;[;mPHPeaXxubP=Nq8%#,_F-SI(Eewc@G3o|WG&PTVf0z3]=l!6V%F(FAW11kuP~c#",
                    encrypt=True,
                    sslValidateCertificate=False
                )
        
        cursor = conn.cursor()
        cursor.execute(SQL)

        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]

        df = pd.DataFrame(rows, columns=columns)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name='report.xlsx',
        )

@app.route("/",methods=['POST','OPTIONS'])
def home():

    print("Method:", request.method)
    print("Content-Type:", request.headers.get("Content-Type"))

    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True)
    print("JSON:", data)

    # return jsonify({
    #                 "msg": "# Approved Vendor Payments Overview\n\nHere’s the summary of the approved vendor payments from the database, focusing on those with a payment status of **\"Paid.\"** \n\n## Key Findings\n\n- **Total Number of Approved Payments:** 14\n- **Total Amount Paid:** **₹ 17,400,000**\n- **Payment Dates:** Payments span from **April 15, 2025** to **February 15, 2026.**\n\n## Detailed Payments List\n\n| VENDOR NAME          | VENDOR CODE | PAYMENT STATUS | AMOUNT (₹) | PAYMENT DATE |\n|----------------------|-------------|----------------|-------------|--------------|\n| Tata Steel           | V001        | Paid           | 1,250,000   | 2025-04-15   |\n| Siemens AG           | V002        | Paid           | 980,000     | 2025-04-26   |\n| ABB Ltd              | V003        | Paid           | 1,850,000   | 2025-05-10   |\n| Flowserve India      | V005        | Paid           | 760,000     | 2025-06-05   |\n| Emerson Electric     | V006        | Paid           | 1,420,000   | 2025-06-20   |\n| BHEL                 | V007        | Paid           | 1,680,000   | 2025-07-05   |\n| GE Vernova           | V010        | Paid           | 880,000     | 2025-08-15   |\n| Tata Steel           | V001        | Paid           | 1,340,000   | 2025-08-28   |\n| Larsen & Toubro     | V004        | Paid           | 2,100,000   | 2025-09-30   |\n| BHEL                 | V007        | Paid           | 1,480,000   | 2025-11-10   |\n| Thermax Ltd          | V008        | Paid           | 1,620,000   | 2025-11-25   |\n| GE Vernova           | V010        | Paid           | 1,850,000   | 2025-12-18   |\n| Tata Steel           | V001        | Paid           | 1,540,000   | 2025-12-30   |\n| Larsen & Toubro     | V004        | Paid           | 1,360,000   | 2026-02-15   |\n\n## Insights\n\n- **Top Vendor by Amount:** **Larsen & Toubro** received the highest payment of **₹ 2,100,000**.\n- **Repeat Payments:** **Tata Steel** and **BHEL** appear multiple times, indicating ongoing business relationships.\n- **Payment Distribution:** The payments are relatively evenly distributed over the months, maintaining a consistent cash flow.\n\nIf you need further analysis or details about specific vendors, feel free to ask! 📊",
    #                 "success": True})

    data = request.get_json()
    print(data)
    user_question = data.get('question',None)
    if not user_question:
        return jsonify({'success':False,'msg':"Paylode Content Type Faild!"})

    res1 = call_openai_get_sql(user_question)

    if not res1.get('success'):
        return jsonify({'success':False,'msg':res1.get('error')})

    if not res1.get('data').get('status'):

        reply = classify_user_question(user_question)

        if reply.get('success'):
            return jsonify({'success':True,'msg':"I’m not able to answer that, but I can help you with anything related to Procurement Analytics. Please try again with a relevant question.",'excel':False})

        return jsonify({'success':True,'msg':reply.get('msg'),'excel':False})
        
    res2 = hana_db_sql_execution(res1.get('data').get('SQL'))

    if not res2.get('success'):
        return jsonify({'success':False,'msg':res1.get('error')})

    res3 = call_openai_get_reply(user_question,res1.get('data').get('SQL'),res2.get('result'))

    if not res3.get('success'):
        return jsonify({'success':False,'msg':res3.get('error')})

    return jsonify({'success':True,'msg':res3.get('reply'),'excel':True})


# @app.route("/")
# def index():
#     return jsonify({'success':True})

if __name__ == "__main__":
    # context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    # app.run(host='0.0.0.0', port=5000, ssl_context=context,debug=True)
    app.run(host='0.0.0.0', debug=True, port=5000)
