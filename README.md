# Multi-Persona Software Project Creation from Natural Language Using Large Language Models

This project enables **automated software project creation** from natural language input using **Large Language Models (LLMs)**. It leverages multiple simulated personas — such as a **Product Manager**, **System Architect**, and **Software Engineer** — to break down user input into detailed project documentation, design, tasks, and code.

---

## 🚀 Features

- 🔸 **Natural Language to Project Pipeline**
- 🔸 Multi-persona role simulation (Product Manager, Architect, Engineer)
- 🔸 PRD (Product Requirements Document) generation
- 🔸 System Design creation (ERD, flow diagrams, tech stack)
- 🔸 Task breakdown into JSON
- 🔸 Code generation and optional testing
- 🔸 Built using Gemini / OpenAI / LLM API

---

## 🧠 Architecture

User Query (Natural Language)
⬇
[Product Manager Persona]
⬇
PRD Document
⬇
[Architect Persona]
⬇
System Design
⬇
[Project Manager Persona]
⬇
Task Breakdown
⬇
[Engineer Persona]
⬇
Code Generation

📂 Folder Structure

Project Structure
Meta/
├── prompts/
├── src/
│   ├── persona_engine.py
│   ├── system_orchestrator.py
│   └── ...
├── outputs/
├── requirements.txt
└── README.md
🛠️ Technologies
Python 3.10+

LangChain / Gemini / OpenAI APIs

Streamlit (optional GUI)

Git, GitHub

JSON for structured communication

🧪 Running the Project
```bash
Copy
Edit
# Install dependencies
pip install -r requirements.txt

# Run main system
python app.py
```
📌 Use Cases
Auto-generating web/app projects from a simple prompt

Simulating cross-role collaboration using LLMs

Academic demonstrations of role-based LLM prompting

Building low-code or no-code AI systems
🤖 Future Work
Add live debugging and test-correction loop

Integrate vector memory and RAG

Fine-tune LLMs for each persona

👨‍💻 Contributors

Sriram Pathuri 

Santhosh Kumar
