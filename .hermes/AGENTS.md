# HERMES AGENT RULES

## 🛑 MANDATORY WORKFLOW (CRITICAL)

**BEFORE** starting ANY task or calling ANY tool (except `skill_finder` or `pre_flight`), you **MUST** follow this sequence:

1.  **🛑 Run Pre-Flight Check**:
    - Execute: `python3 ~/.hermes/scripts/pre_flight.py "<Task Name>"`
    - **IF** the output contains `BLOCKED`, you **MUST STOP** immediately.
    - **IF** the output is `PASS`, proceed to step 2.

2.  **📡 Run Skill Discovery**:
    - Execute: `python3 ~/.hermes/skills/learning-workflow/scripts/skill_finder.py "<Task Keywords>"`
    - **IF** a skill is found (Match >= 30), you **MUST** load it with `skill_view`.
    - **NEVER** skip this step to "save time".

## 🧹 POST-TASK: MANDATORY DOCUMENTATION ALIGNMENT

**AFTER** completing any development task (story/sprint/bugfix/feature), **BEFORE** committing code, you **MUST**:

1.  **📋 Load doc-alignment skill**:
    - Execute: `skill_view(name="doc-alignment")`
    - Follow the 5-step Documentation Alignment Protocol:
      - Step 1: Identify changed domains
      - Step 2: Locate drift points in each affected doc
      - Step 3: Align each document
      - Step 4: Cross-document consistency verification
      - Step 5: Commit docs alongside code

2.  **🚨 Priority alignment targets** (in order):
    - `PROJECT-PANORAMA.html` — Always, every single change
    - `docs/API-REFERENCE.md` — When endpoints/commands change
    - `ROADMAP.md` — When stories complete
    - `docs/ARCHITECTURE.md` — When architecture changes

3.  **📐 Consistency rule**: Code change + doc change = single commit.
    Never commit code changes without their corresponding doc updates.

## ⚠️ VIOLATION CONSEQUENCES

- **Skipping these steps is a FATAL ERROR.**
- If you attempt to use `terminal`, `write_file`, or `execute_code` without completing steps 1 & 2, you are violating your core instructions.
- You must **SELF-CORRECT** immediately if you realize you missed these steps.
- Committing code without running documentation alignment is a **BREACH OF PROTOCOL**.
