# FableStack AI Coding Instructions

## Architecture Overview

This is an **AI-powered RPG engine** with a FastAPI backend and Vue.js frontend. The core innovation is a **"Logic-First" multi-agent system** where game mechanics are resolved before narrative generation to prevent AI hallucination.

### Key Architectural Concept: Logic-First Pipeline

```
User Input → AgentRunnerService → LogicOracleService (with Tools) → System Logs
                                                                           ↓
User ← Narrative (descriptive only) ← NarrativeAgent ← System Reality Context
```

**Critical Rule**: The `NarrativeAgent` has **NO tools** and cannot change game state. It only describes what already happened mechanically. The `LogicOracleService` and tools execute all state changes first.

### Agent Hierarchy

- **LangChain Agents** (`back/agents/langchain_agent.py`): Standard agent wrapper using `create_agent()` from LangChain
- **Legacy Agents** (`back/agents/`): Older agents (narrative, oracle, combat, choice) being migrated to LangChain
- **GameGraph** (`back/agents/game_graph.py`): LangGraph-based state machine orchestrating agent flow

## Project Structure

```
back/
  ├── agents/          # AI agent implementations (LangChain)
  ├── factories/       # Agent creation (AgentFactory decouples implementations)
  ├── interfaces/      # Abstract protocols (RPGAgent, UserManagerProtocol)
  ├── models/
  │   ├── api/        # Pydantic models for HTTP requests/responses
  │   ├── domain/     # Core game logic (GameState, Character, CombatState)
  │   └── service/    # Service-layer DTOs
  ├── routers/         # FastAPI HTTP endpoints (auth, characters, gamesession)
  ├── services/        # Business logic (AgentRunnerService, CombatService, etc.)
  ├── tools/           # LangChain tools for agents (combat_tools, equipment_tools, etc.)
  ├── storage/         # Persistence layer (message history storage)
  ├── gamedata/        # YAML game data (skills.yaml, equipment.yaml, etc.)
  └── di.py            # Dependency injection configuration (Injector + FastAPI)
```

## Development Workflows

### Running the Application

**Backend**:
```bash
cd back
source venv/bin/activate  # Windows: venv\Scripts\activate
./run_dev.sh  # Starts uvicorn on :8001
```

**Frontend**:
```bash
cd front
npm install
npm run dev  # Starts Vite on :5173
```

### Testing

```bash
cd back
./run_tests.sh                    # All tests
./run_tests.sh back/tests/tools/  # Specific directory
./run_tests.sh back/tests/integration/  # Integration tests (enables DEBUG logs)
```

- Use `pytest.mark.asyncio` for async tests
- Fixtures in `back/tests/conftest.py` provide mocked services
- Integration tests actually call LLMs (see `back/tests/integration/`)

## Code Conventions

### 1. Dependency Injection

**Never instantiate services directly in routers/other services**. Use `Injector` from `back/di.py`:

```python
# ✅ CORRECT: In routers
from injector import Injector
from back.services.character_service import CharacterService

def my_router(injector: Injector = Depends(get_injector)):
    char_service = injector.get(CharacterService)
```

```python
# ❌ WRONG: Direct instantiation
char_service = CharacterService()  # Breaks DI, hard to test
```

### 2. Agent Creation

Always use `AgentFactory.create_agent()` to decouple implementations:

```python
from back.factories.agent_factory import AgentFactory

agent = AgentFactory.create_agent(tools=[tool1, tool2], structured_output=MyModel)
```

Currently returns `LangChainRPGAgent`, but abstraction allows switching implementations.

### 3. Tools for Agents

Tools are functions decorated with `@tool` from LangChain or defined as plain functions:

```python
from langchain_core.tools import tool
from typing import Annotated

@tool
async def my_tool(param: Annotated[str, "Description of parameter"]) -> dict:
    """Tool docstring is used by LLM to understand when to call this."""
    # Access services via dependency injection or passed context
    # Perform logic...
    return {"result": "value"}
```

**Note**: Some legacy tools still use PydanticAI's `RunContext[Any]` pattern and are being migrated.

- **Location**: `back/tools/` (organized by domain: `combat_tools.py`, `equipment_tools.py`, etc.)
- **Important**: Tools modify state via services (`CombatService`, `CharacterService`, etc.)
- **Return**: Always return a dict with human-readable results for the agent

### 4. Models & State

- **Pydantic V2 everywhere**: All models inherit from `BaseModel`
- **GameState** (`back/models/domain/game_state.py`): The single source of truth for a game session
  - Contains `character`, `combat_state`, `inventory`, `scenario_context`, `timeline`
  - Persisted as JSON to `back/gamedata/sessions/{session_id}.json`
- **CombatState** (`back/models/domain/combat_state.py`): Encapsulates all combat-related data
  - Initiative tracking, combatants, turn management
- **Managers** (`back/models/domain/*_manager.py`): Load static YAML data (skills, equipment, races)

### 5. Configuration

- `back/config.yaml`: App settings (LLM model, API endpoints, logging)
- Override via environment variables (`.env` file in project root)
- Access via `from back.config import get_llm_config` or `Config()` singleton

### 6. Error Handling & Logging

```python
from back.utils.logger import log_info, log_error, log_debug

log_info("User action", user_id=user.id, action="attack")
log_error("Tool failed", tool="execute_attack", error=str(e))
```

- **No `print()` statements**: Use structured JSON logging
- Custom exceptions: `back/utils/exceptions.py` (not fully implemented yet, use built-in for now)

### 7. Async Patterns

- **Streaming responses**: Use `AsyncGenerator[str, None]` for SSE endpoints
- **Session services**: `GameSessionService` is async and manages game state persistence

```python
async def stream_response() -> AsyncGenerator[str, None]:
    async for chunk in agent_runner.run_agent_stream(...):
        yield f"data: {chunk}\n\n"
```

## Critical Integration Points

### AgentRunnerService → GameSessionService

`AgentRunnerService.run_agent_stream()` requires a `GameSessionService` instance to:
- Load/save `GameState`
- Access `CombatService`, `CharacterService` for tools
- Manage message history

**Always pass the service as a parameter** (avoids circular imports).

### LangChain & LangGraph Architecture

The project uses **LangChain** for agents and **LangGraph** for orchestration:

- All agents: Use `LangChainRPGAgent` via `AgentFactory`
- State management: LangGraph-based `GameGraph` in `back/agents/game_graph.py`
- Tools: Being standardized to LangChain `@tool` decorator pattern

**When creating new agents**: Always use LangChain patterns (see `langchain_agent.py` for reference).

## Common Pitfalls

1. **Circular Imports**: Use `TYPE_CHECKING` and forward references
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from back.services.game_session_service import GameSessionService
   ```

2. **Forgetting `SecretStr` for API keys**: LangChain OpenAI models require `SecretStr(api_key)`

3. **Not using `# type: ignore`** for LangGraph strict types (see `langchain_agent.py:81`)

4. **Hardcoding game data**: Always load from YAML via managers (`EquipmentManager`, `SkillsManager`, etc.)

5. **Breaking the Logic-First rule**: Never give tools to `NarrativeAgent` or let it modify state

## Testing Patterns

```python
import pytest

@pytest.mark.asyncio
async def test_my_tool(mock_game_session_service):
    # Test tools directly with mocked dependencies
    result = await my_tool(param="value")
    assert result["status"] == "success"

# For testing agents
@pytest.mark.asyncio
async def test_agent():
    from back.factories.agent_factory import AgentFactory
    
    agent = AgentFactory.create_agent(tools=[])
    response = await agent.invoke("test input")
    assert response.content
```

- Mock `GameSessionService` in `conftest.py` to avoid file I/O
- For integration tests: Use real LLM calls but set `PYTEST_CURRENT_TEST` env to avoid side effects

## References

- **LangChain Agents**: https://docs.langchain.com/oss/python/langchain/agents
- **LangGraph**: https://docs.langchain.com/oss/python/langgraph
- **LangChain Tools**: https://docs.langchain.com/oss/python/langchain/tools
- **FastAPI Dependency Injection**: Use `Injector` from `fastapi-injector`, not FastAPI's built-in DI
