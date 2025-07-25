<<<<<<< HEAD
import gradio as gr
from dotenv import load_dotenv
import os
import time

from utils.extract_text import extract_text_from_file
from utils.summarize import generate_financial_summary
from utils.parse_kpis import extract_kpis_from_text
from utils.pdf_report import generate_pdf
from utils.qa_agent import build_qa_chain_from_text

load_dotenv()
qa_agent = None  # Global QA chain
uploaded_file_path = None  # Track uploaded file

# --------------------------
# 📄 Handle Upload
# --------------------------
def handle_upload(file):
    global qa_agent, uploaded_file_path

    # Reset UI elements initially
    yield gr.update(value=""), None, gr.update(visible=False), gr.update(selected=0) # Clear previous outputs, hide PDF, keep on upload tab

    if file is None:
        return gr.update(value="❌ Error: No file uploaded. Please select a file."), None, gr.update(visible=False), gr.update(selected=0)

    uploaded_file_path = file.name
    
    # Show processing message
    yield gr.update(value="### ⏳ Processing file... This may take a moment."), None, gr.update(visible=False), gr.update(selected=0)
    
    try:
        # Step 1: Extract Text
        yield gr.update(value="### ⏳ Extracting text from file..."), None, gr.update(visible=False), gr.update(selected=0)
        extracted_text = extract_text_from_file(uploaded_file_path)
        if not extracted_text or not extracted_text.strip():
            raise ValueError("No readable text extracted from the file after processing. The file might be empty or unreadable.")

        # Step 2: Generate Summary
        yield gr.update(value="### ⏳ Generating executive summary..."), None, gr.update(visible=False), gr.update(selected=0)
        summary = generate_financial_summary(extracted_text)
        if not summary or "Error generating summary" in summary: # Check for specific error message from summarize.py
            raise RuntimeError(f"Failed to generate summary: {summary}")

        # Step 3: Extract KPIs
        yield gr.update(value="### ⏳ Extracting Key Performance Indicators (KPIs)..."), None, gr.update(visible=False), gr.update(selected=0)
        kpis, ratios = extract_kpis_from_text(extracted_text)

        # Step 4: Generate PDF Report
        yield gr.update(value="### ⏳ Generating downloadable PDF report..."), None, gr.update(visible=False), gr.update(selected=0)
        pdf_path = generate_pdf(summary, kpis, ratios)
        if not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF report could not be generated. Please check server logs.")

        # Step 5: Build Q&A Agent
        yield gr.update(value="### ⏳ Building Q&A agent for interactive querying..."), None, gr.update(visible=False), gr.update(selected=0)
        qa_agent = build_qa_chain_from_text(extracted_text)
        print("✅ QA agent created successfully.")

        # Prepare final output
        output = f"### 📘 Executive Summary:\n\n{summary}\n"
        output += "\n---\n\n### 📊 Key Financial KPIs:\n"
        
        if kpis:
            for key, value in kpis.items():
                # Format numbers for better readability
                if isinstance(value, (int, float)):
                    output += f"- **{key}**: {value:,.2f}\n"
                else: # For N/A or non-numeric values
                    output += f"- **{key}**: {value}\n"
        else:
            output += "⚠️ No significant financial KPIs could be extracted.\n"


        if ratios:
            output += "\n### 📈 Financial Ratios:\n"
            for key, value in ratios.items():
                output += f"- **{key}**: {value}\n"
        else:
            output += "\n⚠️ No financial ratios found or computable."
        
        # Return final state
        yield gr.update(value=output), gr.update(value=pdf_path, visible=True), gr.update(visible=True), gr.update(selected=1)

    except FileNotFoundError as e:
        error_msg = f"❌ File Error: {str(e)}"
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)
    except ValueError as e:
        error_msg = f"❌ Data Error: {str(e)}"
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)
    except RuntimeError as e:
        error_msg = f"❌ Processing Error: {str(e)}"
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)
    except Exception as e:
        error_msg = f"❌ An unexpected error occurred during upload: {str(e)}. Please try again or check server logs."
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)


# --------------------------
# 💬 Handle Q&A
# --------------------------
def answer_question(user_question):
    global qa_agent

    print("📩 Question:", user_question)
    
    if qa_agent is None:
        yield gr.update(value="❌ Please upload a file first and wait for processing to complete.")
        return
        
    if not user_question.strip():
        yield gr.update(value="❌ Please enter a valid question.")
        return

    # Show processing message
    yield gr.update(value="### ⏳ Getting answer...")
    
    try:
        response = qa_agent.invoke({"query": user_question})
        print("🤔 Raw LLM Response:", response)

        answer = response.get("result", "").strip()

        if not answer or answer == "I am sorry, but the answer to your question is not available in the provided document excerpts.":
            final_answer_display = "### 🔍 Answer:\n\n" + "I am sorry, but the answer to your question is not available in the provided document excerpts or cannot be reliably determined from the document."
            yield gr.update(value=final_answer_display)
            return

        final_answer_display = f"### 🔍 Answer:\n\n{answer}"
        
        # --- REMOVED / COMMENTED OUT THE SOURCE DISPLAY SECTION ---
        # source_docs = response.get("source_documents", [])
        # if source_docs:
        #     final_answer_display += "\n\n---\n\n### 📚 Sources:\n"
        #     for i, doc in enumerate(source_docs):
        #         content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        #         final_answer_display += f"- Source {i+1}: \"{content_preview}\"\n"

        # Debugging prints (you can remove these once confirmed working)
        print(f"DEBUG: Final answer display content length: {len(final_answer_display)}")
        print(f"DEBUG: Final answer display content (first 500 chars): {final_answer_display[:500]}")
        
        yield gr.update(value=final_answer_display)

    except Exception as e:
        print("❌ QA error:", e)
        yield gr.update(value=f"❌ Error answering question: {str(e)}. Please try re-uploading the document or a different question.")

# --------------------------
# ⬆️ Reset Handler
# --------------------------
def reset_all():
    global qa_agent, uploaded_file_path
    qa_agent = None
    uploaded_file_path = None
    # Reset all relevant UI components
    return gr.update(value=""), None, gr.update(value="", visible=False), gr.File(value=None), gr.update(value="")

# --------------------------
# 🎨 Gradio UI
# --------------------------
with gr.Blocks(css="""
    .gr-box { border-width: 1px !important; }
    .gradio-container { padding: 1rem !important; }
    .gr-button { font-weight: bold; }
    h3 { margin-top: 1.5rem; }
""") as demo:
    gr.Markdown("# 🤔 Financial Document Analyzer") # Updated project name here
    gr.Markdown("Upload a financial file (PDF, Word, Excel, TXT, or Image) to get an AI-generated executive summary, KPIs, and ask questions.")

    tab_state = gr.State(0)

    with gr.Tab("📄 Upload & Summary", id="upload_tab"):
        file_input = gr.File(label="📄 Upload Financial File", file_types=[".pdf", ".docx", ".txt", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"])
        submit_upload = gr.Button("🚀 Submit")
        output_display = gr.Markdown()
        pdf_download = gr.File(label="📅 Download AI Report", visible=False, file_count="single")
        reset_button_upload = gr.Button("🔄 Reset")

    with gr.Tab("💬 Ask a Question", id="qa_tab"):
        user_input = gr.Textbox(label=None, placeholder="E.g., What was the net profit?", lines=2)
        ask_button = gr.Button("🔍 Get Answer")
        answer_display = gr.Markdown()
        reset_button_question = gr.Button("🔄 Reset")

    # Connect components
    submit_upload.click(
        fn=handle_upload,
        inputs=[file_input],
        outputs=[output_display, pdf_download, pdf_download, tab_state],
        show_progress="hidden"
    )

    ask_button.click(
        fn=answer_question,
        inputs=[user_input],
        outputs=[answer_display],
        show_progress="hidden"
    )
    
    # Input clearing for Q&A (currently commented out based on your preference)
    # ask_button.click(lambda: "", outputs=[user_input], queue=False)

    reset_button_upload.click(
        fn=reset_all,
        inputs=[],
        outputs=[output_display, pdf_download, answer_display, file_input, user_input]
    )

    reset_button_question.click(
        fn=reset_all,
        inputs=[],
        outputs=[output_display, pdf_download, answer_display, file_input, user_input]
    )

=======
import gradio as gr
from dotenv import load_dotenv
import os
import time

from utils.extract_text import extract_text_from_file
from utils.summarize import generate_financial_summary
from utils.parse_kpis import extract_kpis_from_text
from utils.pdf_report import generate_pdf
from utils.qa_agent import build_qa_chain_from_text

load_dotenv()
qa_agent = None  # Global QA chain
uploaded_file_path = None  # Track uploaded file

# --------------------------
# 📄 Handle Upload
# --------------------------
def handle_upload(file):
    global qa_agent, uploaded_file_path

    # Reset UI elements initially
    yield gr.update(value=""), None, gr.update(visible=False), gr.update(selected=0) # Clear previous outputs, hide PDF, keep on upload tab

    if file is None:
        return gr.update(value="❌ Error: No file uploaded. Please select a file."), None, gr.update(visible=False), gr.update(selected=0)

    uploaded_file_path = file.name
    
    # Show processing message
    yield gr.update(value="### ⏳ Processing file... This may take a moment."), None, gr.update(visible=False), gr.update(selected=0)
    
    try:
        # Step 1: Extract Text
        yield gr.update(value="### ⏳ Extracting text from file..."), None, gr.update(visible=False), gr.update(selected=0)
        extracted_text = extract_text_from_file(uploaded_file_path)
        if not extracted_text or not extracted_text.strip():
            raise ValueError("No readable text extracted from the file after processing. The file might be empty or unreadable.")

        # Step 2: Generate Summary
        yield gr.update(value="### ⏳ Generating executive summary..."), None, gr.update(visible=False), gr.update(selected=0)
        summary = generate_financial_summary(extracted_text)
        if not summary or "Error generating summary" in summary: # Check for specific error message from summarize.py
            raise RuntimeError(f"Failed to generate summary: {summary}")

        # Step 3: Extract KPIs
        yield gr.update(value="### ⏳ Extracting Key Performance Indicators (KPIs)..."), None, gr.update(visible=False), gr.update(selected=0)
        kpis, ratios = extract_kpis_from_text(extracted_text)

        # Step 4: Generate PDF Report
        yield gr.update(value="### ⏳ Generating downloadable PDF report..."), None, gr.update(visible=False), gr.update(selected=0)
        pdf_path = generate_pdf(summary, kpis, ratios)
        if not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF report could not be generated. Please check server logs.")

        # Step 5: Build Q&A Agent
        yield gr.update(value="### ⏳ Building Q&A agent for interactive querying..."), None, gr.update(visible=False), gr.update(selected=0)
        qa_agent = build_qa_chain_from_text(extracted_text)
        print("✅ QA agent created successfully.")

        # Prepare final output
        output = f"### 📘 Executive Summary:\n\n{summary}\n"
        output += "\n---\n\n### 📊 Key Financial KPIs:\n"
        
        if kpis:
            for key, value in kpis.items():
                # Format numbers for better readability
                if isinstance(value, (int, float)):
                    output += f"- **{key}**: {value:,.2f}\n"
                else: # For N/A or non-numeric values
                    output += f"- **{key}**: {value}\n"
        else:
            output += "⚠️ No significant financial KPIs could be extracted.\n"


        if ratios:
            output += "\n### 📈 Financial Ratios:\n"
            for key, value in ratios.items():
                output += f"- **{key}**: {value}\n"
        else:
            output += "\n⚠️ No financial ratios found or computable."
        
        # Return final state
        yield gr.update(value=output), gr.update(value=pdf_path, visible=True), gr.update(visible=True), gr.update(selected=1)

    except FileNotFoundError as e:
        error_msg = f"❌ File Error: {str(e)}"
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)
    except ValueError as e:
        error_msg = f"❌ Data Error: {str(e)}"
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)
    except RuntimeError as e:
        error_msg = f"❌ Processing Error: {str(e)}"
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)
    except Exception as e:
        error_msg = f"❌ An unexpected error occurred during upload: {str(e)}. Please try again or check server logs."
        print(error_msg)
        yield gr.update(value=error_msg), None, gr.update(visible=False), gr.update(selected=0)


# --------------------------
# 💬 Handle Q&A
# --------------------------
def answer_question(user_question):
    global qa_agent

    print("📩 Question:", user_question)
    
    if qa_agent is None:
        yield gr.update(value="❌ Please upload a file first and wait for processing to complete.")
        return
        
    if not user_question.strip():
        yield gr.update(value="❌ Please enter a valid question.")
        return

    # Show processing message
    yield gr.update(value="### ⏳ Getting answer...")
    
    try:
        response = qa_agent.invoke({"query": user_question})
        print("🤔 Raw LLM Response:", response)

        answer = response.get("result", "").strip()

        if not answer or answer == "I am sorry, but the answer to your question is not available in the provided document excerpts.":
            final_answer_display = "### 🔍 Answer:\n\n" + "I am sorry, but the answer to your question is not available in the provided document excerpts or cannot be reliably determined from the document."
            yield gr.update(value=final_answer_display)
            return

        final_answer_display = f"### 🔍 Answer:\n\n{answer}"
        
        # --- REMOVED / COMMENTED OUT THE SOURCE DISPLAY SECTION ---
        # source_docs = response.get("source_documents", [])
        # if source_docs:
        #     final_answer_display += "\n\n---\n\n### 📚 Sources:\n"
        #     for i, doc in enumerate(source_docs):
        #         content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        #         final_answer_display += f"- Source {i+1}: \"{content_preview}\"\n"

        # Debugging prints (you can remove these once confirmed working)
        print(f"DEBUG: Final answer display content length: {len(final_answer_display)}")
        print(f"DEBUG: Final answer display content (first 500 chars): {final_answer_display[:500]}")
        
        yield gr.update(value=final_answer_display)

    except Exception as e:
        print("❌ QA error:", e)
        yield gr.update(value=f"❌ Error answering question: {str(e)}. Please try re-uploading the document or a different question.")

# --------------------------
# ⬆️ Reset Handler
# --------------------------
def reset_all():
    global qa_agent, uploaded_file_path
    qa_agent = None
    uploaded_file_path = None
    # Reset all relevant UI components
    return gr.update(value=""), None, gr.update(value="", visible=False), gr.File(value=None), gr.update(value="")

# --------------------------
# 🎨 Gradio UI
# --------------------------
with gr.Blocks(css="""
    .gr-box { border-width: 1px !important; }
    .gradio-container { padding: 1rem !important; }
    .gr-button { font-weight: bold; }
    h3 { margin-top: 1.5rem; }
""") as demo:
    gr.Markdown("# 🤔 Financial Document Analyzer") # Updated project name here
    gr.Markdown("Upload a financial file (PDF, Word, Excel, TXT, or Image) to get an AI-generated executive summary, KPIs, and ask questions.")

    tab_state = gr.State(0)

    with gr.Tab("📄 Upload & Summary", id="upload_tab"):
        file_input = gr.File(label="📄 Upload Financial File", file_types=[".pdf", ".docx", ".txt", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"])
        submit_upload = gr.Button("🚀 Submit")
        output_display = gr.Markdown()
        pdf_download = gr.File(label="📅 Download AI Report", visible=False, file_count="single")
        reset_button_upload = gr.Button("🔄 Reset")

    with gr.Tab("💬 Ask a Question", id="qa_tab"):
        user_input = gr.Textbox(label=None, placeholder="E.g., What was the net profit?", lines=2)
        ask_button = gr.Button("🔍 Get Answer")
        answer_display = gr.Markdown()
        reset_button_question = gr.Button("🔄 Reset")

    # Connect components
    submit_upload.click(
        fn=handle_upload,
        inputs=[file_input],
        outputs=[output_display, pdf_download, pdf_download, tab_state],
        show_progress="hidden"
    )

    ask_button.click(
        fn=answer_question,
        inputs=[user_input],
        outputs=[answer_display],
        show_progress="hidden"
    )
    
    # Input clearing for Q&A (currently commented out based on your preference)
    # ask_button.click(lambda: "", outputs=[user_input], queue=False)

    reset_button_upload.click(
        fn=reset_all,
        inputs=[],
        outputs=[output_display, pdf_download, answer_display, file_input, user_input]
    )

    reset_button_question.click(
        fn=reset_all,
        inputs=[],
        outputs=[output_display, pdf_download, answer_display, file_input, user_input]
    )

>>>>>>> 071cbec525ec210f6e1ec0ab118281bfd30b0780
    demo.launch()