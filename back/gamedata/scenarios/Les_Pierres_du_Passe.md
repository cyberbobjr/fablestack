---
id: "scen_pierres_passe"
title: "Les Pierres du Passé"
---

# Scenario: Les Pierres du Passé

## Context

L’histoire se déroule en l’année 2955 du Troisième Âge, dans les collines d’Evendim, au nord-ouest de la Comté.
Les ruines de l’ancien royaume d’Arnor abritent des mystères anciens et des légendes sombres.
Les habitants du village d’Esgalbar sont en proie à des disparitions et des rumeurs de présences maléfiques.

---

## 1. Locations

### Village d’Esgalbar

- **Description** :
  - Petit hameau de maisons en bois et torchis, bordé de champs en friche et de collines. Une palissade sommaire entoure le village, témoignage de la peur qui règne.
  - Une petite place centrale est dominée par une fontaine sèche, entourée de quelques échoppes et maisons modestes.
- **Ambiance** : Le silence est oppressant, et les villageois évitent de sortir après le crépuscule. Une brume matinale semble ne jamais se lever complètement.
- **NPCs** :
  - **Thadric le forgeron** :
    - **Race ID** : `humans`
    - Homme robuste d’une quarantaine d’années, cheveux noirs grisonnants, mains calleuses.
    - *Personality* : Protecteur envers ses proches, mais désabusé par les récents événements.
    - *Interaction* : Fournit des armes de base et des informations sur les disparitions.
  - **Berilwen l’herboriste** :
    - **Race ID** : `humans`
    - Femme âgée, frêle, aux cheveux gris argent attachés en un chignon. Elle porte une robe usée mais propre, ornée de motifs végétaux.
    - *Personality* : Enigmatique et sage, elle inspire le respect.
    - *Interaction* : Partage des récits sur les "Pierres du Passé" et propose des potions simples (antidotes ou remèdes).

### Collines d’Evendim

- **Description** :
  - Collines accidentées parsemées de rochers moussus et de bosquets de hêtres tordus. Un vent glacial souffle souvent dans la région.
  - Des sentiers peu visibles serpentent à travers la lande, conduisant à des ruines isolées.
- **Possible Encounters** : Loups affamés ou brigands errants.

### Les Ruines d’Arnor

- **Tour effondrée** :
  - Ancienne tour de guet dont il ne reste qu’une moitié de muraille et des pierres éparpillées. Une arche intacte mène à un escalier descendant.
  - *Indices* : Une corde usée (trace récente de passage) et des symboles elfiques gravés sur la pierre.
- **Sanctuaire souterrain** :
  - Salle voûtée éclairée par une faible lumière phosphorescente émanant de mousses. Des colonnes brisées jonchent le sol.
  - *Points d’intérêt* :
    - Un autel orné de pierres bleutées et de motifs runiques.
    - Deux prisonniers enfermés dans une cage rouillée.

---

## 2. NPCs & Creatures

### Thorvil le pillard

- **Race ID** : `humans`
- **Appearance** : Homme dans la trentaine, cheveux longs et sales, visage dur et marqué par des cicatrices. Armé d’une dague et d’un vieux bouclier.
- **Personality** : Opportuniste, rusé mais nerveux. Il est en quête de trésors mais n’est pas un meurtrier de sang-froid.
- **Interaction** :
  - *Amical* : Si le joueur le convainc, il peut devenir un allié temporaire.
  - *Hostile* : Si le joueur le menace ou refuse de partager les trouvailles.

### Halric et Mara (les disparus)

- **Race ID** : `humans`
- **Halric** : Garçon de 14 ans, cheveux roux ébouriffés, vêtement de laine déchiré. Il tremble de peur mais tente de rester courageux.
- **Mara** : Fille de 12 ans, cheveux bruns nattés, visage sale mais déterminé. Elle tente de cacher sa panique.
- *Interaction* : Les deux sont reconnaissants si sauvés mais trop effrayés pour aider.

### Le spectre des Tumulus

- **Race ID** : `spectre`
- **Appearance** : Silhouette translucide, yeux brillants d’une lueur verte, flottant à quelques centimètres du sol. Armé d’une épée spectrale.
- **Personality** : Un ancien noble d’Arnor corrompu par la malédiction. Sa voix est un murmure froid.
- **Pouvoirs** :
  - Aura de peur (jets pour résister).
  - Résistance élevée sauf aux armes magiques ou en argent.
  - Peut être apaisé si un artefact lui est restitué.

---

## 3. Items & Rewards

- **Pierres du Passé** (ID: `item_runic_stones`):
  - Deux pierres runiques bleutées. Elles confèrent un bonus temporaire de +5 en Raisonnement si portées.
  - **Attribution Condition** : Trouvées sur l'autel du Sanctuaire souterrain. Le joueur peut les prendre après avoir vaincu ou apaisé le Spectre, ou en réussissant un test de Discrétion.
- **Épée ancienne** (ID: `weapon_ancient_sword`):
  - Une épée d’Arnor gravée, légèrement rouillée. Bonus de +5 au combat contre les morts-vivants.
  - **Attribution Condition** : Trouvée dans la Tour effondrée en fouillant les décombres (test de Fouille réussi) ou donnée par **Thadric** si les joueurs le persuadent de leur confier une arme efficace contre le mal.
- **Broche enchantée** (ID: `item_enchanted_brooch`):
  - Amulette en argent augmentant la résistance mentale contre les effets de peur.
  - **Attribution Condition** : Offerte par **Berilwen l’herboriste** avant le départ des joueurs vers les Ruines d'Arnor, en guise de protection contre les esprits.

---

## 4. Random Encounters

| d6 | Encounter | Race ID |
|----|-----------|---------|
| 1-2 | Rien | - |
| 3-4 | Loups | `wolf` |
| 5 | Brigands | `humans` |
| 6 | Marchand ambulant | `humans` |

---

## 5. Progression & XP

- **Explorer les ruines** : 20 XP.
- **Trouver et sauver les disparus** : 50 XP.
- **Combattre ou apaiser le spectre** : 70 XP.
- **Décision morale (pierres)** : 20 XP.
