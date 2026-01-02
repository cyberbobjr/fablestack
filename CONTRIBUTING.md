# Contributing to the Middle‑earth RPG (JdR)

Thanks for your interest in improving the project! This one‑page guide summarizes how to propose changes effectively.

## 1. Core Principles

- Single Responsibility: every service/file has one clear concern.
- Separation of Concerns: Routers = HTTP only, Services = business logic, Managers = YAML data loading, Agents/Tools = LLM orchestration, Storage = persistence.
- Type Safety Everywhere: Python with full type hints + Pydantic models.
- English Only: code, comments, docs, data.
- No Hardcoded Game Data: always use managers under `back/models/domain/*_manager.py`.

## 2. Getting Started

```bash
# Backend
cd back
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API docs: <http://localhost:8000/docs>. Frontend will be recreated later.

## 3. Branching & Commits

- Branch naming: `feat/<short-description>`, `fix/<issue-id-or-desc>`, `docs/...`, `refactor/...`, `test/...`.
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `perf:`, `chore:`.
- Keep commits focused; prefer several small logical commits over one large mixed commit.

## 4. Backend Code Standards

- Pydantic V2 models with validators and explicit error messages.
- Docstrings (Google style) for every public function/method. MUST include:
  - **Purpose**: Why the method exists in 3 sentences minimum
  - **Args**: All arguments with types and descriptions.
  - **Returns**: Return value type and description.
  - **Language**: English only.
- Services: no file or network I/O (delegate to persistence/storage classes).
- Avoid circular dependencies—prefer dependency injection passing services explicitly.
- Logging: use JSON logger (`back/utils/logger.py`); never `print()`.
- Exceptions: raise custom ones from `utils/exceptions.py`.
- Async: use `async` for I/O (file, network, CPU-bound stays sync unless justified).

<!-- Frontend code standards not applicable: frontend removed for now -->

## 6. Testing

```bash
# Backend tests
cd back && pytest tests/ -v
```

- Mirror source structure: add tests under matching folder (e.g. `back/tests/routers/`).
- New service or model == new test module.
- Avoid mocking managers unless necessary; prefer real YAML fixtures.
- Keep tests deterministic (no real LLM calls—mock or isolate tool logic).

## 7. Pull Request Guidelines

Include: purpose, high‑level approach, any schema changes, migration steps. PR Checklist:

- [ ] Follows SRP & layering rules
- [ ] Added/updated tests (and they pass)
- [ ] Updated docs/README if behavior or endpoints changed
- [ ] No hardcoded game data
- [ ] Logging & exceptions consistent
- [ ] Type hints & docstrings added
<!-- Frontend build step omitted: frontend removed for now -->

## 8. Issues & Feature Requests

- Search existing issues before opening new ones.
- Provide reproduction steps, expected vs actual behavior, environment details.
- Label appropriately: `bug`, `enhancement`, `docs`, `question`.

## 9. Security & Sensitive Data

- Do not commit API keys or secrets; use environment variables.
- Validate all external input; never trust raw request data.
- Report vulnerabilities privately first (open a minimal placeholder issue if needed).

## 10. LLM / Agent Changes

- Keep system prompt modifications minimal and documented.
- Persist history only through `PydanticJsonlStore`; never duplicate system prompts in storage.
- When adding tools: include clear docstring, deterministic return shape, and tests for tool edge cases.

## 11. Performance

- Avoid N+1 file or YAML loads—reuse manager instances.
- Defer heavy computation; prefer caching if needed (submit separate performance PR if large change).

## 12. Style & Hygiene

- Run minimal linting/formatting (e.g., black/ruff if configured; otherwise maintain existing style).
- Remove dead code & commented blocks before review.

## 13. LLM Tool Coding Standards

These rules are critical for ensuring that the LLM can correctly understand and utilize the tools provided to it.

### 1. Explicit Function Names

- **Rule**: Function names must be descriptive and clearly indicate the action and the target.
- **Good**: `inventory_add_item`, `skill_check_with_character`, `list_available_equipment`
- **Bad**: `add`, `check`, `get_list`, `update_stuff`
- **Why**: The LLM uses the function name as a primary signal for semantic relevance.

### 2. Detailed Docstrings

- **Rule**: Every tool MUST have a docstring that explains **WHEN** to use it, **WHAT** it does, and **HOW** to use it.
- **Format**:

    ```python
    def tool_name(ctx, arg1: type, arg2: type = default) -> return_type:
        """
        Short summary of the action.

        Detailed explanation of the tool's purpose, when it should be triggered,
        and any side effects (e.g., gold deduction, saving data).

        Args:
            arg1 (type): Clear description of the argument. Constraints (e.g., "must be English").
            arg2 (type): Description. Default value explanation.

        Returns:
            return_type: Description of the return value structure.
        """
    ```

- **Why**: The docstring is the "instruction manual" for the LLM. It helps the model disambiguate between similar tools and construct valid calls.

### 3. Typed Parameters with Descriptions

- **Rule**: All parameters must have Python type hints and be fully described in the `Args` section of the docstring.
- **Constraints**: If a parameter has constraints (e.g., "English only", "positive integer"), these MUST be explicitly stated in the docstring.
- **Defaults**: Clearly state default values and their behavior.
- **Why**: Type hints and descriptions allow the LLM to generate the correct JSON schema and avoid `ValidationErrors`.

### 4. Return Values

- **Rule**: Tools should return a dictionary or a Pydantic model that provides a clear, structured summary of the action's result.
- **Error Handling**: If an error occurs, return a dictionary with an `"error"` key and a helpful message/suggestion, rather than raising an unhandled exception (unless it's a critical system failure).
- **Why**: Structured feedback allows the LLM to confirm success or understand why a failure occurred and retry if necessary.

### 5. System Prompt Guidance

- **Rule**: The system prompt should explicitly guide the LLM on the *workflow* of using tools (e.g., "Check inventory before removing items", "List equipment before buying").
- **Why**: While docstrings explain *individual* tools, the system prompt explains the *orchestration* and *policy* of using them.

---
By submitting a contribution you agree to follow these guidelines. Thank you for helping build the Middle‑earth RPG!
