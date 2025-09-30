import os
from typing import List, TypedDict
from groq import Groq
import numpy as np
from sentence_transformers import SentenceTransformer
import tkinter as tk
from tkinter import scrolledtext, messagebox

# ========================
# CONFIGURATION
# ========================
GROQ_API_KEY = "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"
MODEL_NAME = "llama-3.3-70b-versatile"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = BASE_DIR  # assuming TXT files are here

client = Groq(api_key=GROQ_API_KEY)
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# ========================
# STATE DEFINITION
# ========================
class AgentState(TypedDict, total=False):
    question: str
    files_used: List[str]
    answer: str

# ========================
# AGENT FUNCTIONS
# ========================
def select_files(state: AgentState, top_k: int = 5) -> AgentState:
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".txt")]
    if not files:
        messagebox.showerror("Error", "No TXT files found in data folder.")
        return state

    file_contents = [open(os.path.join(DATA_FOLDER, f), "r", encoding="utf-8").read() for f in files]

    # Embeddings
    file_embeddings = embed_model.encode(file_contents, convert_to_tensor=True)
    question_embedding = embed_model.encode(state["question"], convert_to_tensor=True)

    similarities = np.dot(file_embeddings, question_embedding) / (
        np.linalg.norm(file_embeddings, axis=1) * np.linalg.norm(question_embedding)
    )
    top_indices = similarities.argsort()[-top_k:][::-1]
    state["files_used"] = [files[i] for i in top_indices]
    return state

def analyze(state: AgentState) -> AgentState:
    text_content = ""
    for f in state["files_used"]:
        with open(os.path.join(DATA_FOLDER, f), "r", encoding="utf-8") as fp:
            text_content += f"\n--- {f} ---\n" + fp.read()

    prompt = f"""
You are a project management assistant.
Question: {state['question']}
Use the following project data from files:
{text_content}

Provide a clear and concise answer with reasoning.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    state["answer"] = response.choices[0].message.content
    return state

# ========================
# GUI FUNCTIONS
# ========================
def ask_question_gui():
    question = question_entry.get()
    if not question.strip():
        return
    state = AgentState()
    state["question"] = question

    output_text.configure(state='normal')
    output_text.delete(1.0, tk.END)
    output_text.insert(tk.END, "Processing...\n")
    output_text.update()

    try:
        state = select_files(state)
        state = analyze(state)
        answer = state.get("answer", "No answer")
        files_used = state.get("files_used", [])

        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"📌 Answer:\n{answer}\n\n📂 Files used:\n{files_used}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    output_text.configure(state='disabled')

# ========================
# BUILD TKINTER GUI
# ========================
root = tk.Tk()
root.title("Project Management Assistant")
root.geometry("700x500")

tk.Label(root, text="Enter your project management question:").pack(pady=5)

question_entry = tk.Entry(root, width=80)
question_entry.pack(pady=5)
question_entry.focus()

ask_button = tk.Button(root, text="Ask", command=ask_question_gui)
ask_button.pack(pady=5)

output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=25, state='disabled')
output_text.pack(padx=10, pady=10)

root.mainloop()
