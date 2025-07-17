import os
import json
import subprocess
import re
from deepseek_client import configure_api, invoke_persona

KNOWLEDGE_BASE_DIR = 'knowledge_base'

# Ensure knowledge base directory exists
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

def retrieve_context(user_prompt, top_k=2):
    """Simple keyword search over .txt/.md files in knowledge_base/. Returns top_k most relevant snippets."""
    files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(('.txt', '.md'))]
    scored = []
    for fname in files:
        path = os.path.join(KNOWLEDGE_BASE_DIR, fname)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Score by keyword overlap
        score = sum(1 for word in user_prompt.lower().split() if word in content.lower())
        if score > 0:
            scored.append((score, content[:1500]))  # Limit snippet size
    scored.sort(reverse=True)
    return '\n---\n'.join([s[1] for s in scored[:top_k]]) if scored else ''

def augment_prompt(user_prompt):
    context = retrieve_context(user_prompt)
    if context:
        return f"Relevant context from knowledge base:\n{context}\n\nUser request: {user_prompt}"
    return user_prompt

def read_prompt_template(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def run_pytest_on_file(test_file_path, cwd):
    try:
        result = subprocess.run([
            'pytest', test_file_path, '--maxfail=1', '--disable-warnings', '-q'
        ], cwd=cwd, capture_output=True, text=True)
        return (result.returncode == 0, result.stdout + result.stderr)
    except Exception as e:
        return (False, str(e))

def run_orchestrator(user_idea, progress_callback=None):
    try:
        configure_api()
    except ValueError as e:
        if progress_callback:
            progress_callback(f"Error: {str(e)}")
        return {'status': 'error', 'message': str(e)}

    # Sanitize project name for directory
    project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', user_idea.strip().lower())
    project_dir = os.path.join('.', project_name)
    os.makedirs(project_dir, exist_ok=True)
    status_log = []
    # PHASE 1: PLANNING & DESIGN
    if progress_callback:
        progress_callback('Generating PRD...')
    pm_prompt_template = read_prompt_template('prompts/product_manager.txt')
    pm_prompt = pm_prompt_template.format(user_idea=user_idea)
    prd_text = invoke_persona(pm_prompt)
    prd_file_path = os.path.join(project_dir, 'prd.md')
    with open(prd_file_path, 'w', encoding='utf-8') as f:
        f.write(prd_text)
    status_log.append(f"PRD saved to '{prd_file_path}'")

    if progress_callback:
        progress_callback('Generating System Design...')
    architect_prompt_template = read_prompt_template('prompts/architect.txt')
    architect_prompt = architect_prompt_template.format(prd_content=prd_text)
    system_design = invoke_persona(architect_prompt)
    system_design_path = os.path.join(project_dir, 'system_design.md')
    with open(system_design_path, 'w', encoding='utf-8') as f:
        f.write(system_design)
    status_log.append(f"System Design saved to '{system_design_path}'")

    # PHASE 2: TASK BREAKDOWN
    if progress_callback:
        progress_callback('Breaking down tasks...')
    pm_task_prompt_template = read_prompt_template('prompts/project_manager.txt')
    pm_task_prompt = pm_task_prompt_template.format(prd_content=prd_text, system_design=system_design)
    task_json = invoke_persona(pm_task_prompt)
    try:
        task_json_clean = task_json.strip()
        task_json_clean = re.sub(r'^(json|```json|```)', '', task_json_clean, flags=re.IGNORECASE).strip()
        task_json_clean = re.sub(r'```$', '', task_json_clean).strip()
        tasks = json.loads(task_json_clean)
    except Exception as e:
        status_log.append("Failed to parse task JSON. Output was:\n" + task_json)
        if progress_callback:
            progress_callback('Failed to parse task JSON.')
        return {'status': 'error', 'log': status_log}
    status_log.append(f"Parsed {len(tasks)} tasks.")

    # PHASE 3: CODE GENERATION
    if progress_callback:
        progress_callback('Generating code files...')
    engineer_prompt_template = read_prompt_template('prompts/engineer.txt')
    generated_files = []
    for i, task in enumerate(tasks):
        file_name = task['file_name']
        task_description = task['task_description']
        if progress_callback:
            progress_callback(f"Generating {file_name}...")
        engineer_prompt = engineer_prompt_template.format(
            file_name=file_name,
            task_description=task_description,
            prd_content=prd_text,
            system_design=system_design
        )
        os.makedirs(os.path.dirname(os.path.join(project_dir, file_name)), exist_ok=True)
        code = invoke_persona(engineer_prompt)
        # Clean code for any file type
        code = clean_code(code, file_name)
        file_path = os.path.join(project_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        generated_files.append(file_name)
        status_log.append(f"{file_name} generated.")

    # PHASE 4: QUALITY ASSURANCE
    if progress_callback:
        progress_callback('Generating unit tests...')
    qa_prompt_template = read_prompt_template('prompts/qa_engineer.txt')
    test_files = []
    for file_name in generated_files:
        file_path = os.path.join(project_dir, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_code = f.read()
        except Exception as e:
            status_log.append(f"Could not read {file_name}: {e}")
            continue
        qa_prompt = qa_prompt_template.format(
            file_name=file_name,
            prd_content=prd_text,
            system_design=system_design,
            file_code=file_code
        )
        if progress_callback:
            progress_callback(f"Generating test for {file_name}...")
        test_code = invoke_persona(qa_prompt)
        test_file_name = f"test_{file_name.replace('.py', '')}.py"
        test_file_path = os.path.join(project_dir, test_file_name)
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        test_files.append((file_name, test_file_name))
        status_log.append(f"{test_file_name} generated.")

    # PHASE 5: CODE FIXER / DEBUGGER LOOP
    if progress_callback:
        progress_callback('Running tests and fixing code if needed...')
    code_fixer_prompt_template = read_prompt_template('prompts/code_fixer.txt')
    for file_name, test_file_name in test_files:
        test_file_path = os.path.join(project_dir, test_file_name)
        file_path = os.path.join(project_dir, file_name)
        for attempt in range(2):
            if progress_callback:
                progress_callback(f"Testing {file_name} (attempt {attempt+1})...")
            success, output = run_pytest_on_file(test_file_path, cwd=project_dir)
            if success:
                status_log.append(f"Tests passed for {file_name}!")
                break
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_code = f.read()
                    with open(test_file_path, 'r', encoding='utf-8') as f:
                        test_code = f.read()
                except Exception as e:
                    status_log.append(f"Could not read code or test for fixer: {e}")
                    break
                fixer_prompt = code_fixer_prompt_template.format(
                    file_name=file_name,
                    file_code=file_code,
                    test_code=test_code,
                    error_message=output
                )
                if progress_callback:
                    progress_callback(f"Fixing {file_name}...")
                fixed_code = invoke_persona(fixer_prompt)
                # Clean code for any file type
                fixed_code = clean_code(fixed_code, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                status_log.append(f"{file_name} updated by Code Fixer.")
        else:
            status_log.append(f"Could not fix {file_name} after 2 attempts.")

    if progress_callback:
        progress_callback('Project generation complete!')
    status_log.append("Project generation complete!")
    return {'status': 'success', 'log': status_log, 'project_dir': project_dir}

def clean_code(code, file_name):
    """
    Remove any non-code text after the last code block for any file type.
    For .js, .ts, .java, .c, .cpp, .cs: after last '}'.
    For .py, .sh, .rb, .go, .php, .html, .css, .json, .md, .txt: after last non-empty, non-comment line.
    Otherwise, just return the code as is.
    """
    if not code:
        return code
    ext = file_name.split('.')[-1].lower()
    if ext in ['js', 'ts', 'java', 'c', 'cpp', 'cs']:
        last_brace = code.rfind('}')
        if last_brace != -1:
            return code[:last_brace+1]
        return code
    elif ext in ['py', 'sh', 'rb', 'go', 'php', 'html', 'css', 'json', 'md', 'txt']:
        lines = code.splitlines()
        last_code_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                last_code_idx = i
        if last_code_idx != -1:
            return '\n'.join(lines[:last_code_idx+1])
        return code
    else:
        return code 