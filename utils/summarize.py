import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_financial_summary(text):
    if not text:
        return "No text provided for summarization."

    # Refined prompt for more targeted and structured summaries
    prompt = f"""
    You are an expert financial analyst. Your task is to provide a concise and insightful executive summary of the following financial data.

    **Focus on the most critical financial aspects:**
    1.  **Overall Financial Health:** Briefly describe the general state of the company's finances (e.g., strong, stable, facing challenges).
    2.  **Key Figures:** Summarize the most recent Total Assets, Total Liabilities, and Shareholder Equity.
    3.  **Profitability:** Highlight the Net Profit/Net Income and Revenue.
    4.  **Liquidity:** Comment on Cash and Cash Equivalents.
    5.  **Risks & Opportunities (if clearly stated or inferable from figures):** Mention any significant risks, red flags, or notable growth opportunities. If no specific risks are mentioned, state that based on the provided data, no explicit risks were identified.

    **Instructions:**
    -   Keep the summary to 3-5 concise paragraphs.
    -   Use clear, professional, and easy-to-understand language.
    -   Do NOT make up any information. If a specific detail is not present in the text, do not include it or explicitly state it's not available.
    -   Prioritize factual statements over generic observations.

    --- BEGIN FINANCIAL DATA ---
    {text}
    --- END OF DATA ---

    Executive Summary:
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",  # Best free model with large context
            temperature=0.3,         # Lower temperature for more factual, less creative output
            max_tokens=500           # Limit output length to encourage conciseness
        )

        summary_content = chat_completion.choices[0].message.content.strip()

        if not summary_content:
            return "No summary content returned by the model."

        return summary_content

    except Exception as e:
        # More specific error messages for common issues
        if "rate limit" in str(e).lower():
            return "❌ Error: API rate limit exceeded. Please try again shortly."
        elif "invalid api key" in str(e).lower() or "authentication" in str(e).lower():
            return "❌ Error: Invalid or missing API key. Please check your .env file."
        elif "context_length_exceeded" in str(e).lower(): # Though llama3-70b has a large window, good to catch
            return "❌ Error: The document is too long for the AI model to process. Please try a shorter document."
        else:
            return f"❌ Error generating summary: {str(e)}"