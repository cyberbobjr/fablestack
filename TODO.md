# Project Analysis: Improvements & Features

Based on the analysis of the `jdr` project (FastAPI backend + Vue.js frontend), here are the recommended improvements and features.

## 10 Technical Improvements

### 1. Frontend Testing Suite (Vitest)

* **Synthesis**: The frontend lacks a testing framework. Implementing Vitest (unit/component tests) and potentially Cypress/Playwright (e2e) is crucial for reliability.
* **Effort**: **Medium**. setup is quick, but writing initial tests takes time.
* **Pros**: Catch regressions early, document component behavior, safer refactoring.
* **Cons**: Initial time investment, maintenance of test code.

### 2. Database Migration (SQLite/PostgreSQL)

* **Synthesis**: Currently using file-based storage (JSON/JSONL). Migrating to a proper SQL database (via SQLAlchemy or Prisma) would improve data integrity, query capability, and concurrency.
* **Effort**: **High**. Requires rewriting `GameSessionService` and storage layers.
* **Pros**: ACID transactions, complex queries (e.g., "all mages level 5+"), better scalability, easier backups.
* **Cons**: increased infrastructure complexity, migration scripts needed.

### 3. Strict Service Return Types (DTOs)

* **Synthesis**: Some services return raw `dict` or `Tuple`. Refactor all Services to return strict Pydantic models (DTOs) to ensure type safety across the entire backend.
* **Effort**: **Medium**. monotonous refactoring work.
* **Pros**: Better IDE autocompletion, fail-fast on data errors, cleaner API documentation (if exposed).
* **Cons**: slightly more boilerplate code.

### 4. Centralized Error Handling Middleware

* **Synthesis**: Replace scattered `try/except` blocks in Routers with a global Exception Handler middleware that maps custom Exceptions to HTTP codes and standardizes error responses.
* **Effort**: **Low**.
* **Pros**: Cleaner router code, consistent error response structure for frontend, centralized logging.
* **Cons**: Risk of masking unexpected errors if not configured carefully.

### 5. Automated API Client Generation

* **Synthesis**: Use tools like `openapi-ts` (Hey-API) to automatically generate the TypeScript client from the FastAPI `openapi.json` schema.
* **Effort**: **Low**.
* **Pros**: Frontend types always match Backend, zero boilerplate for API calls, faster development.
* **Cons**: Requires build pipeline step; changes in backend break frontend build (good thing!).

### 6. Frontend Code Quality (ESLint/Prettier)

* **Synthesis**: Add and enforce `eslint` and `prettier` configs for the Vue project to ensure consistent code style and catch potential bugs (e.g., unused vars, reactivity issues) locally.
* **Effort**: **Low**.
* **Pros**: Consistent codebase, automatic formatting, catches simple bugs pre-commit.
* **Cons**: Initial "fixing" of existing lint errors might be annoying.

### 7. Structured Configuration (Pydantic Settings)

* **Synthesis**: Move all hardcoded configuration (CORS origins, file paths, constants) into a central `Settings` class using `pydantic-settings`, loading from `.env`.
* **Effort**: **Low**.
* **Pros**: Type-safe config, validation of environment variables on startup, central source of truth.
* **Cons**: None really.

### 8. CI/CD Workflow (GitHub Actions)

* **Synthesis**: Create a `.github/workflows/ci.yml` file to run backend tests (`pytest`), frontend build, and linters on every push/PR.
* **Effort**: **Medium**.
* **Pros**: Prevents broken code from reaching main, enforces quality standards automatically.
* **Cons**: Requires CI runner time (usually free for public/small private repos).

### 9. Scenario Validation Tooling

* **Synthesis**: Create a CLI script or Pydantic model validator that parses `SCENARIO.md` files to ensure they strictly follow the format (IDs exist, headers are correct) before loading them.
* **Effort**: **Medium**.
* **Pros**: Content creators get immediate feedback, prevents runtime crashes due to bad scenario files.
* **Cons**: Maintenance of the validation logic.

### 10. Async Logic Optimization & Dependency Injection

* **Synthesis**: Review `GlobalContainer` usage. Move towards a more robust DI framework (like `fastapi-injector`) or refine the current singleton pattern to be more testable. Ensure all I/O is strictly async.
* **Effort**: **Medium**.
* **Pros**: Better test isolation (mocking dependencies becomes easier), cleaner architecture.
* **Cons**: Learning curve for DI frameworks.

---

## 5 Gameplay Features

### 1. Immersive AI Audio (Voice & Soundscape)

* **Synthesis**: Integrate Text-to-Speech (ElevenLabs/OpenAI) for the Narrator/NPCs and Speech-to-Text (Whisper) for player input.
* **Effort**: **Medium/High** (API integration + Frontend Audio handling).
* **Pros**: Massive immersion boost, accessibility.
* **Cons**: API costs, latency management.

### 2. Generative Visuals (Dynamic Scene Art)

* **Synthesis**: Use DALL-E 3 or Stable Diffusion to generate images for Locations, NPCs, and Items on the fly (or pre-generate them when the scenario is loaded).
* **Effort**: **Medium**.
* **Pros**: "Wow" factor, helps visual thinkers, makes the UI pop.
* **Cons**: API costs, potential for weird AI artifacts, generation time.

### 3. Campaign Mode (Persistent World)

* **Synthesis**: Link scenarios together. Decisions in Scenario A affect Scenario B (e.g., "You killed the Goblin King, so the Orcs are disorganized in the next session"). Manage a "Campaign State".
* **Effort**: **High**.
* **Pros**: Deep long-term engagement, meaningful player choices.
* **Cons**: Complex state management and writing requirements.

### 4. Companion/Party System

* **Synthesis**: Allow the player to recruit AI-controlled companions (NPCs) that persist across sessions.
* **Effort**: **High**.
* **Pros**: Classic RPG feel, tactile tactical depth in combat.
* **Cons**: Complicates the turn loop and UI.
* **Implementation Plan**:
    1.  **Data Models**:
        *   Add `COMPANION` to `CombatantType` enum in `back/models/domain/combat_state.py`.
        *   **Companion Schema**: Create a dedicated `Companion` model (inheriting from `NPC` or `Character`) that includes:
            *   `personality`: Structured traits (e.g., "Cynical", "Brave") to drive AI behavior/dialogue.
            *   `history`: A log of significant events specific to this companion (e.g., "Saved by player in Goblin Cave").
            *   `relationship_score`: Numeric value tracking affinity with the player.
        *   Create a `Party` model or extend `GameSession` to persist a list of these full `Companion` objects.
    2.  **Mechanics & Logic**:
        *   **Recruitment**: Implement a social skill check (Persuasion/Diplomacy). Success initializes a `Companion` instance with generated personality/history.
        *   **Limits**: Enforce a hard limit of **5** companions.
        *   **Mortality**: Companions are mortal. Death is permanent and removed from the active party (but potentially archived in history).
    3.  **Architecture & Agents**:
        *   **Create `CompanionAgent`**: A dedicated agent responsible solely for **Narrative** interactions (dialogue, social reactions).
        *   **Combat Split**: The `Combat Agent` retains control during combat for efficiency and rule adherence.
        *   **Output Format**: Companion responses are generated as distinct "Chat Events" (like player messages), not merged into the narrator's text block.
    4.  **Persistence**:
        *   **Full State Storage**: Ensure the entire `Companion` object (stats, inventory, personality, history) is serialized into the `User` or `GameSession` storage, ensuring they evolve and remember past events across sessions.
    5.  **Prompt Integration & Agency**:
        *   **Companion Prompt**: The `CompanionAgent` receives specific context (history, traits, current situation) to generate authentic reactions.
        *   **Combat Prompt**: Ensure `CombatState` includes `COMPANION` types with full stat blocks in the `[ALLIES]` section.
        *   **Interference (Agency)**:
            *   *Narrative*: The `CompanionAgent` decides when to "speak up" based on personality triggers.
            *   *Combat*: The `Logic Oracle` must accept commands *for* companions (e.g., "I order Dwarf to attack"). If no command is given, the `Combat Agent` autonomously generates their turn based on archetype.

### 5. Reputation & Faction System

* **Synthesis**: Track player standing with different factions (e.g., "Kingdom", "Rebels"). Actions shift these values, unlocking/locking interactions or store items.
* **Effort**: **Medium**.
* **Pros**: Adds political depth and consequences to roleplay.
* **Cons**: Needs UI visualization and logic integration into the Oracle/Narrative checks.
