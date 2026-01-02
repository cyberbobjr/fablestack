# Product Vision: AI Backend RPG

## Vision

Create a tireless virtual Game Master (GM), capable of offering personalized, coherent, and mechanically rigorous adventures at any time. The system combines the narrative flexibility of LLMs with the rigor of a classic RPG rules engine.

## Targets

- **Solo Players**: To test builds or experience a quick adventure.
- **GM-less Groups**: To play cooperatively with an AI as referee.
- **Developers**: A robust API to build RPG frontends.

## Current Functional Scope

### 1. Assisted Character Creation

- Complete creation (Race, Class, Stats, Equipment).
- Strict rule validation.
- JSON persistence.

### 2. Game Engine (Backend)

- **Combat System**: Turn-based, initiative, HP management, attacks, damage.
- **State Management**: Saving and resuming combats (`CombatStateService`).
- **Inventory**: Buying, selling, equipping, quantity management (ammo, consumables) (`EquipmentService`).
- **Preferences**: User settings management (`SettingsService`).

### 3. Narration & AI

- **Narrative Agent**: Handles exploration and dialogue.
- **Combat Agent**: Takes over during clashes, manages enemy strategy.
- **Orchestration**: Fluid transition between narration and combat via Pydantic Graph.

## Differentiators

- **Hybrid**: Not just a chatbot, but a real game engine with rules enforced by code.
- **Persistent**: The world and characters "exist" beyond the LLM context window.
- **Transparent**: Dice rolls and calculations are exposed, not hallucinated.

## Product Maturity

- **Backend**: 🟢 Stable (Core features implemented).
- **Rules**: 🟡 Partial (Basic combat functional, simplified Magic).
- **AI**: 🟢 Functional (Specialized agents in place).

## Short Term Roadmap

1. **Bestiary Enrichment**: More monsters and special abilities.
2. **Complex Scenarios**: Support for multi-session campaigns with structured metadata (ID, Title).
3. **Frontend**: Development of a graphical user interface (Web/Mobile).

## Success Metrics

- **Rule Validity**: 100% of created characters are legal.
- **Stability**: No crashes during Narration <-> Combat transitions.
- **Performance**: Agent response time < 5s.

## Game Mechanics

### Skill System (d100)

The system uses a 100-sided die (d100) where the player must obtain a result lower than or equal to their target.

**Target Calculation Formula:**
$$
\text{Target} = (\text{Base Stat} \times 3) + (\text{Skill Rank} \times 10) - \text{Difficulty}
$$

**Details:**

- **Base Stat**: Associated characteristic (e.g., Strength for Melee). Multiplier x3.
- **Skill Rank**: Training level (0 to 5+). Multiplier x10.
- **Difficulty**:
  - *Favorable*: -20 (Bonus of +20%)
  - *Normal*: 0
  - *Unfavorable*: +20 (Penalty of -20%)

**Example:**
Agility 14 + Rank 2 + Normal Difficulty = $(14 \times 3) + (2 \times 10) - 0 = 62\%$ chance.

### Character Creation

#### 1. Characteristics (Stats)

The system uses a scale of **3 to 20** (similar to D&D).

- **Maximum Total Sum**: 60 points.

- **Generation**: Random (between 8 and 15) or manual assignment.
- **Modifier**: `(Value - 10) // 2`.
  - *Example*: Strength 16 gives a +3 bonus.

#### 2. Skills

Each character has a global budget of **40 skill points**, distributed as follows:

1. **Racial Affinities**: Fixed points granted by race (e.g., Elves +3 in Perception).
2. **Stat Bonuses**: Bonus points if the associated stat is high.
   - **Mechanism**: Each skill can have a threshold (`min_value`) for a given stat. If the character's stat reaches this threshold, they receive bonus points (`bonus_points`) in that skill.
   - *Example*: "Storytelling" has a bonus based on Charisma with `min_value: 14` and `bonus_points: 3`. If the character has 14+ in Charisma, they start with +3 in Storytelling.
3. **Free Points**: The remainder of the 40 points is distributed freely (or randomly) into available skills.

### Combat

- **Initiative**: `Dexterity (Mod) + (Wisdom (Mod) // 2)`.
- **Armor Class (AC)**: `10 + Dexterity (Mod) + Armor Bonus`.
- **Hit Points (HP)**: `Constitution x 10 + Level x 5`.
- **Mana Points (MP)**: `Intelligence x 5 + Wisdom x 3`.
- **Attack**:
  - Melee: `d20 + Strength (Mod) + Proficiency Bonus`.
  - Ranged: `d20 + Dexterity (Mod) + Proficiency Bonus`.
- **Damage**: Depends on weapon + `Strength (Mod)` (for melee).
