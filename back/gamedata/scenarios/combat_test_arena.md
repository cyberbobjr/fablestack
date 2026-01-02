---
id: "scen_combat_arena"
title: "Arène de Combat (Test)"
---

# Scenario: Arène de Combat

## Context

Ceci est un scénario de test technique conçu pour éprouver les mécaniques de combat.
L'environnement est une arène abstraite hors du temps et de l'espace.
Le but est de tester les limites du système de combat, les résistances des créatures et la puissance des items.

---

## 1. Locations

### L'Armurerie (Zone de Départ)

- **Description**:
  - Une salle circulaire en pierre blanche immaculée.
  - Sur les murs, des râteliers d'armes présentent tout l'équipement standard.
  - Au centre, un piédestal noir supporte un anneau unique qui semble vibrer de puissance.
- **Ambiance**: Calme, froide, artificielle. Une lumière zénithale éclaire la pièce sans source visible.
- **NPCs**: Aucun.
- **Possible Encounters**: Aucune. C'est une zone sûre.

### L'Arène de Sang

- **Description**:
  - Une vaste fosse de sable rouge entourée de gradins bondés de spectateurs fantomatiques.
  - Des portails magiques aux quatre coins crépitent, prêts à libérer des créatures.
- **Ambiance**: Une tension vibrante. Les hurlements de la foule couvrent le bruit des armes. L'odeur du sang et de l'ozone sature l'air.
- **Possible Encounters**:
  - Les portails peuvent invoquer des vagues d'ennemis sur commande (ou via les rencontres aléatoires).

---

## 2. NPCs & Creatures

### Guerrier Orc de Test

- **Race ID**: `orc`
- **Appearance**: Un orc massif en armure de plaques rouillée. Il grogne et frappe son bouclier.
- **Personality**: Agressif et stupide. Il ne connaît que le combat.
- **Interaction**:
  - *Hostile*: Attaque à vue.

### Meute de Loups

- **Race ID**: `wolf`
- **Appearance**: Trois loups gris aux yeux jaunes, bavant et montrant les crocs.
- **Personality**: Prédateurs affamés. Ils attaquent en groupe.
- **Interaction**:
  - *Hostile*: Encerclent et attaquent.

### Le Spectre Ancien

- **Race ID**: `spectre`
- **Appearance**: Une forme vaporeuse et glaciale.
- **Personality**: Haineux envers toute vie.
- **Interaction**:
  - *Hostile*: Utilise la peur et des attaques drainantes.

### Squelette Armé

- **Race ID**: `skeleton`
- **Appearance**: Un amas d'os animé tenant une épée courte.
- **Personality**: Automate sans âme.
- **Interaction**:
  - *Hostile*: Avance sans peur vers l'ennemi.

---

## 3. Items & Rewards

- **Anneau du Développeur (God Mode)** (ID: `accessory_god_mode_ring`):
  - Un anneau en or pur gravé du symbole de l'infini.
  - **Effect/Bonus**: Lorsqu'il est équipé, le porteur devient virtuellement invincible.
    - +100 en Force, Agilité, Constitution, Intelligence, Volonté et Charisme.
    - Régénération instantanée des PV.
    - Les attaques tuent instantanément les ennemis standards.
  - **Attribution Condition**: Posé sur le piédestal central de l'Armurerie. Disponible dès le début pour permettre le test rapide.

- **Épée Longue Standard** (ID: `weapon_longsword`):
  - Arme standard pour tester les dégâts normaux.
  - **Attribution Condition**: Disposée sur les râteliers de l'Armurerie.

- **Arc Long** (ID: `weapon_longbow`):
  - Arme à distance standard.
  - **Attribution Condition**: Disposée sur les râteliers de l'Armurerie.

- **Potion de Soins** (ID: `item_healing_potion`): # Note: Assuming this ID exists or is generic, based on standard naming convention in equipment.yaml usually
  - Potion rouge standard.
  - **Attribution Condition**: Une caisse de potions est disponible dans l'Armurerie.

---

## 4. Random Encounters

| d6 | Encounter | Race ID |
|----|-----------|---------|
| 1-3 | Orc Solitaire | `orc` |
| 4-5 | Meute de Loups (2-3) | `wolf` |
| 6 | Le Spectre | `spectre` |

---

## 5. Progression & XP

- **Vaincre un Orc** : 50 XP.
- **Vaincre le Spectre** : 100 XP.
- **Survivre à 3 vagues** : 200 XP.
