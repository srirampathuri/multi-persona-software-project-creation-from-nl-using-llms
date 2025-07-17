import os
import json
import subprocess
from deepseek_client import configure_api, invoke_persona
from flask import Flask, render_template, request, jsonify
import threading

def read_prompt_template(file_path: str) -> str:
    """Reads a prompt template from the given file path."""
    with open(file_path, 'r') as f:
        return f.read()

def run_pytest_on_file(test_file_path, cwd):
    """Runs pytest on a specific test file and returns (success, output)."""
    try:
        result = subprocess.run([
            'pytest', test_file_path, '--maxfail=1', '--disable-warnings', '-q'
        ], cwd=cwd, capture_output=True, text=True)
        return (result.returncode == 0, result.stdout + result.stderr)
    except Exception as e:
        return (False, str(e))

def main():
    """Main function to run the Gemini-Team workflow."""
    # 1. Configure the API
    try:
        configure_api()
    except ValueError as e:
        print(e)
        return

    # 2. Get user's idea
    user_idea = input("What software project do you want to build? \n> ")
    if not user_idea:
        print("No input provided. Exiting.")
        return
        
    project_name = user_idea.replace(" ", "_").lower()
    project_dir = os.path.join('.', project_name)
    os.makedirs(project_dir, exist_ok=True)
    print(f"Project directory '{project_dir}' created.")

    # --- PHASE 1: PLANNING & DESIGN ---

    # 3. Run Product Manager Persona
    print("\n[Phase 1.1] 🧑‍💼 Calling Product Manager...")
    pm_prompt_template = read_prompt_template('prompts/product_manager.txt')
    pm_prompt = pm_prompt_template.format(user_idea=user_idea)
    prd_text = invoke_persona(pm_prompt)
    
    prd_file_path = os.path.join(project_dir, 'prd.md')
    with open(prd_file_path, 'w') as f:
        f.write(prd_text)
    print(f"✅ PRD saved to '{prd_file_path}'")

    # 4. Run Architect Persona
    print("[Phase 1.2] 🏗️ Calling Architect...")
    architect_prompt_template = read_prompt_template('prompts/architect.txt')
    architect_prompt = architect_prompt_template.format(prd_content=prd_text)
    system_design = invoke_persona(architect_prompt)
    system_design_path = os.path.join(project_dir, 'system_design.md')
    with open(system_design_path, 'w') as f:
        f.write(system_design)
    print(f"✅ System Design saved to '{system_design_path}'")

    # --- PHASE 2: TASK BREAKDOWN ---
    print("[Phase 2] 📋 Calling Project Manager for task breakdown...")
    pm_task_prompt_template = read_prompt_template('prompts/project_manager.txt')
    pm_task_prompt = pm_task_prompt_template.format(prd_content=prd_text, system_design=system_design)
    task_json = invoke_persona(pm_task_prompt)
    try:
        tasks = json.loads(task_json)
    except Exception as e:
        print("❌ Failed to parse task JSON. Output was:\n", task_json)
        return
    print(f"✅ Parsed {len(tasks)} tasks.")

    # --- PHASE 3: CODE GENERATION ---
    print("[Phase 3] 🛠️ Generating code files...")
    engineer_prompt_template = read_prompt_template('prompts/engineer.txt')
    generated_files = []
    for i, task in enumerate(tasks):
        file_name = task['file_name']
        task_description = task['task_description']
        print(f"  [Task {i+1}/{len(tasks)}] Generating {file_name}...")
        engineer_prompt = engineer_prompt_template.format(
            file_name=file_name,
            task_description=task_description,
            prd_content=prd_text,
            system_design=system_design
        )
        code = invoke_persona(engineer_prompt)
        file_path = os.path.join(project_dir, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"    ✅ {file_name} generated.")
        generated_files.append(file_name)

    # --- PHASE 4: QUALITY ASSURANCE ---
    print("[Phase 4] 🧪 Generating unit tests with QA Engineer...")
    qa_prompt_template = read_prompt_template('prompts/qa_engineer.txt')
    test_files = []
    for file_name in generated_files:
        file_path = os.path.join(project_dir, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_code = f.read()
        except Exception as e:
            print(f"    ⚠️ Could not read {file_name}: {e}")
            continue
        qa_prompt = qa_prompt_template.format(
            file_name=file_name,
            prd_content=prd_text,
            system_design=system_design,
            file_code=file_code
        )
        test_code = invoke_persona(qa_prompt)
        test_file_name = f"test_{file_name.replace('.py', '')}.py"
        test_file_path = os.path.join(project_dir, test_file_name)
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        print(f"    ✅ {test_file_name} generated.")
        test_files.append((file_name, test_file_name))

    # --- PHASE 5: CODE FIXER / DEBUGGER LOOP ---
    print("[Phase 5] 🐞 Running tests and attempting self-correction if needed...")
    code_fixer_prompt_template = read_prompt_template('prompts/code_fixer.txt')
    for file_name, test_file_name in test_files:
        test_file_path = os.path.join(project_dir, test_file_name)
        file_path = os.path.join(project_dir, file_name)
        for attempt in range(2):
            print(f"    ▶️ Running {test_file_name} (attempt {attempt+1})...")
            success, output = run_pytest_on_file(test_file_path, cwd=project_dir)
            if success:
                print(f"      ✅ Tests passed for {file_name}!")
                break
            else:
                print(f"      ❌ Test failed for {file_name}. Attempting to fix...")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_code = f.read()
                    with open(test_file_path, 'r', encoding='utf-8') as f:
                        test_code = f.read()
                except Exception as e:
                    print(f"      ⚠️ Could not read code or test for fixer: {e}")
                    break
                fixer_prompt = code_fixer_prompt_template.format(
                    file_name=file_name,
                    file_code=file_code,
                    test_code=test_code,
                    error_message=output
                )
                fixed_code = invoke_persona(fixer_prompt)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                print(f"      🔄 {file_name} updated by Code Fixer.")
        else:
            print(f"      🚫 Could not fix {file_name} after 2 attempts.")

    print("\n🎉 Project generation complete!")

if __name__ == "__main__":
    main() 