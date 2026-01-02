# JdR - Terres du Milieu (Frontend)

Ce dossier contient le code source de l'interface utilisateur du Jeu de Rôle "Terres du Milieu".

## 🛠️ Installation et Lancement

### Prérequis

- Node.js (v18+)
- npm

### Configuration

L'application peut être configurée via des variables d'environnement. Copiez le fichier `.env.example` vers `.env.local` et ajustez les valeurs selon votre environnement :

```bash
cp .env.example .env.local
```

**Variables d'environnement disponibles :**

- `VITE_API_BASE_URL` : URL de base du backend API (par défaut : `http://localhost:8001`)

**Exemples de configuration :**

```bash
# Développement local
VITE_API_BASE_URL=http://localhost:8001

# Production
VITE_API_BASE_URL=https://api.example.com

# Staging
VITE_API_BASE_URL=https://staging-api.example.com
```

### Installation des dépendances

```bash
npm install
```

### Lancement en développement

```bash
npm run dev
```

L'application sera accessible à l'adresse `http://localhost:5173`.

## 📂 Structure du Projet

- `src/`
  - `components/` : Composants Vue réutilisables (NavBar, Modales, Outils...)
  - `views/` : Pages principales de l'application (Accueil, Jeu, Personnages...)
  - `services/` : Services pour l'API et la gestion des données
  - `stores/` : Gestion d'état (Pinia) - `gameData` centralise toutes les données statiques.
  - `router/` : Configuration des routes (Vue Router)
  - `locales/` : Fichiers de traduction (i18n)
  - `assets/` : Images et ressources statiques

## 🎨 Thème et Styles

L'application utilise **Tailwind CSS** pour le style.
Le thème est configuré dans `tailwind.config.js` avec des couleurs personnalisées pour l'ambiance fantasy :

- `fantasy-dark` : Fond sombre principal
- `fantasy-secondary` : Fond des conteneurs
- `fantasy-accent` : Couleur d'accentuation (rouge/bordeaux)
- `fantasy-gold` : Texte doré pour les titres

Le mode sombre est activé par défaut, mais un toggle est disponible dans les préférences.

## 🌐 Internationalisation

L'application supporte le Français et l'Anglais.

- **UI (Interface Utilisateur)** :
  - Gérée par `vue-i18n`.
  - Les fichiers de traduction sont dans `src/locales/` (ex: `fr.ts`).
  - Utilisation dans les composants : `const { t } = useI18n()` puis `t('ui.ma_clef')`.

- **Données de Jeu (Game Data)** :
  - Gérées par le backend et stockées dans le store Pinia `gameData`.
  - Le store récupère les traductions depuis l'API (`/translation`) au chargement.
  - Utilisation :

    ```typescript
    import { useGameDataStore } from '../stores/gameData'
    const gameDataStore = useGameDataStore()
    // Traduire une compétence, une race, etc.
    const nomTraduit = gameDataStore.translate('stealth', 'skills')
    ```

  - Le store contient les traductions pour : `races`, `cultures`, `skills`, `stats`, `equipment`, `spells`.

## 🧩 Composants Clés

- **NavBar** : Barre de navigation globale avec accès aux préférences.
- **GameView** : Vue principale du jeu, intégrant le chat et la fiche personnage.
- **CharacterSheetView** : Vue détaillée d'un personnage (lecture seule).
- **PreferencesModal** : Modale pour changer la langue et le thème.

## 🔗 API

Les appels API sont centralisés dans `src/services/api.ts`.

### Configuration de l'URL de l'API

L'URL de l'API backend est configurable via des variables d'environnement pour supporter différents environnements de déploiement.

**Configuration locale (développement)** :

Créez un fichier `.env` dans le dossier `front/` :

```bash
VITE_API_BASE_URL=http://localhost:8001
```

**Configuration pour la production** :

Définissez la variable d'environnement `VITE_API_BASE_URL` dans votre environnement de déploiement :

```bash
VITE_API_BASE_URL=https://api.votre-domaine.com
```

**Fichiers de configuration** :

- `.env.example` : Exemple de configuration à copier
- `.env` : Configuration locale (non versionnée)
- `.env.production` : Configuration de production (non versionnée)

La valeur par défaut est `http://localhost:8001` si aucune variable d'environnement n'est définie.
