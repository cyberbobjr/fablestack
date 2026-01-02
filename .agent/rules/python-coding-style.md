---
trigger: always_on
---

## 1. Core Principles

- Single Responsibility: every service/file has one clear concern.
- Separation of Concerns: Routers = HTTP only, Services = business logic, Managers = YAML data loading, Agents/Tools = LLM orchestration, Storage = persistence.
- Type Safety Everywhere: Python with full type hints + Pydantic models.
- English Only: code, comments, docs, data.
- No Hardcoded Game Data: always use managers under `back/models/domain/*_manager.py`.

## 2. Backend Code Standards

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

**Type Hints**: **MANDATORY**. All functions, methods, variables, class properties, and parameters must have explicit type hints. This includes:

- All function parameters and return types
- All class properties (declared at class level)
- All local variables (inline type annotations)
- All loop variables
- All comprehension variables where ambiguous
  **Example:**

  ```python
  class MyService:
      property_name: str  # Class property type hint
      count: int
      
      def __init__(self, name: str) -> None:
          self.property_name = name
          local_var: int = 42  # Local variable type hint
  ```

- **Pydantic Models**: Use for all data structures. Use V2 features like `field_validator`.
- **Async**: Use `async/await` for all I/O operations.
- **Docstrings**: Document all public methods (description, args, returns).
- **FastAPI Route Documentation**: For all FastAPI router endpoints, provide comprehensive docstrings with detailed descriptions, parameter explanations, request/response JSON examples, and error conditions. This ensures complete OpenAPI documentation for API consumers. Include full JSON schemas for requests and responses to facilitate automatic API documentation generation.
- **Error Handling**: Use custom exceptions from `utils/exceptions.py`.
- **File Naming**:
  - Services: `{domain}_service.py`
  - Managers: `{resource}_manager.py`
  - Tools: `{category}_tools.py`

## 3. Testing

```bash
# Backend tests
cd back && pytest tests/ -v
```

- Mirror source structure: add tests under matching folder (e.g. `back/tests/routers/`).
- New service or model == new test module.
- Avoid mocking managers unless necessary; prefer real YAML fixtures.
- Keep tests deterministic (no real LLM calls—mock or isolate tool logic).

## 4. LLM Tool Coding Standards

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
