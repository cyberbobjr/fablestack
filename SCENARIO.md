# Scenario Creation Guide

This document defines the standard format for game engine scenarios. It serves as a reference for content creators and for AI scenario generation.

## File Structure

A scenario file must be in Markdown format (`.md`) and follow this structure:

### 1. Frontmatter (YAML)

Each file must start with a YAML block containing the ID and title.

```yaml
---
id: "unique_scenario_id"  # Example: "scen_shadows_forest"
title: "Scenario Title"
---
```

### 2. Scenario Sections

Content must be organized with the following Markdown headers (H2 `##`):

#### `## Context`

A brief introduction to the story, location, and general atmosphere.

#### `## 1. Locations`

Description of key locations. For each location:

* **Description**: Visual and sensory.
* **Ambiance**: The atmosphere (sound, light, feeling).
* **NPCs**: List of characters present (reference their names).
* **Possible Encounters**: Threats or random events.

#### `## 2. NPCs & Creatures`

Details of non-player characters and monsters. For each entity:

* **Name**
* **Race ID**: **CRITICAL**. Must match a key from `races_and_cultures.yaml` (e.g., `humans`, `elf`, `dwarf`, `orc`, `wolf`, `spectre`).
* **Appearance**: Physical description.
* **Personality**: Character traits and motivations.
* **Interaction**: How they react to the player (Friendly, Hostile, Neutral).

#### `## 3. Items & Rewards`

List of important items.

* **Item Name** (ID: `item_id`)
  * **Description**
  * **Effect/Bonus**
  * **Attribution Condition**: Specifies when/how the item is obtained (e.g., "Found in chest", "Given by NPC after quest"). Critical to prevent premature distribution.
* **Item IDs**:
  * For standard items (swords, potions, etc.), **YOU MUST** use the exact ID from `back/gamedata/equipment.yaml` (e.g., `weapon_longsword`, `item_rations`).
  * For scenario-unique items, create a consistent ID (e.g., `item_dungeon_key`).

#### `## 4. Random Encounters`

A table of encounters to spice up exploration.

* Format: Markdown Table.
* Columns: d6 (or d20), Encounter, Race ID.

#### `## 5. Progression & XP`

List of actions yielding experience.

* **Action**: XP Amount.

---

## Technical Rules (For LLMs and Creators)

### Data References (YAML)

To be compatible with the game engine, you must use the exact IDs defined in the data files:

1. **Races (`races_and_cultures.yaml`)**: Use the exact keys for the `Race ID` field.
    * Examples: `humans`, `elf`, `dwarf`, `hobbit`, `orc`, `goblin`, `wolf`, `bear`, `undead`.
2. **Equipment (`equipment.yaml`)**: Use the exact `id` for items found or sold.
    * Examples: `weapon_shortsword`, `armor_leather`, `item_torch`, `item_healing_potion`.
3. **Skills (`skills.yaml`)**: For skill checks, use the skill ID.
    * Format: `Skill Name (ID) (Difficulty)`
    * Examples: `Stealth (stealth) (12)`, `Persuasion (persuasion) (14)`, `Athletics (athletics) (10)`.
4. **Stats (`stats.yaml`)**: For raw characteristic checks.
    * Format: `Stat (ID) (Difficulty)`
    * Examples: `Strength (Strength) (15)`, `Intelligence (Intelligence) (12)`.

---

## Scenario Creation Prompt (For LLM)

Copy this prompt to generate a new compatible scenario.

```text
You are an expert Game Master and Designer for a text-based RPG.
Your task is to write a complete scenario file in Markdown format, ready to be integrated into the game engine.

**Strict Constraints:**
1.  **Format**: Use exactly the structure defined above (YAML Frontmatter, specific H2 headers).
2.  **Language**: The narrative content must be in French. Technical keys (IDs) remain in English/Code.
3.  **Technical IDs**:
    *   For each NPC/Creature, you MUST specify a valid `Race ID` (e.g., `humans`, `elf`, `orc`, `wolf`).
    *   For each standard item, you MUST use the exact ID from the `equipment.yaml` file (e.g., `weapon_longsword`, `item_potion`).
    *   For checks, use the format: `Name (ID) (Difficulty)`. Use IDs from `skills.yaml` and `stats.yaml`.
4.  **Items**: Each item MUST have a **Attribution Condition** field explaining exactly when the player gets it.
5.  **Creativity**: Create an immersive atmosphere, sensory descriptions, and NPCs with real personality.

**Expected Output Structure:**

---
id: "scen_scenario_name"
title: "Scenario Title"
---

# Scenario: Scenario Title

## Context
...

## 1. Locations
...

## 2. NPCs & Creatures
...

## 3. Items & Rewards
...

## 4. Random Encounters
...

## 5. Progression & XP
...
```
