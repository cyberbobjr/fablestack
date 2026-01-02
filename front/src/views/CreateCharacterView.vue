<script setup lang="ts">
import { ChevronLeft, Dices, Minus, Plus, Save, Sparkles } from 'lucide-vue-next'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Tooltip from '../components/ui/Tooltip.vue'
import { useCharacterBonuses } from '../composables/useCharacterBonuses'
import api from '../services/api'
import { useGameDataStore } from '../stores/gameData'

const router = useRouter()
const route = useRoute()
const store = useGameDataStore()
const loading = ref(false)
const generatingDetails = ref(false)
const races = computed(() => store.races)
const cultures = ref<{ id: string; name: string }[]>([])
const stats = ref<Record<string, { name: string }>>({})
const sexBonuses = ref<Record<string, any>>({})
const skillsData = ref<any>(null)
const activeSkillGroup = ref<string>('')
// const translatingField = ref<string | null>(null) // Track which field is being translated

const isEditing = computed(() => !!route.params.id)
const characterId = computed(() => route.params.id as string)

const form = reactive({
  name: '',
  sex: '',
  race_id: '',
  culture_id: '',
  stats: {} as Record<string, number>,
  skills: {} as Record<string, Record<string, number>>,
  background: '',
  physical_description: '',
  background_localized: '',
  physical_description_localized: ''
})

// --- Bonus Helpers (Composable) ---
const raceId = computed(() => form.race_id)
const cultureId = computed(() => form.culture_id)
const formSex = computed(() => form.sex)
const formStats = computed(() => form.stats)

const {
  getRaceSkillBonus,
  getCultureSkillBonus,
  getSexSkillBonus,
  getStatBonusForSkill
} = useCharacterBonuses(raceId, cultureId, formSex, formStats, sexBonuses)

onMounted(async () => {
  try {
    loading.value = true
    await store.fetchAllData('fr') // Fetch all data including translations

    // Use data from store if available, fallback to local fetch if needed (but store should have it)
    // For now, let's keep local refs but populate them from store or wait for store
    // Actually, simplest is to use store data directly or populate refs from it

    // races.value = (await api.getRaces()).data // Handled by store
    // But better to use store if possible. The store has skills, stats, translations.
    // Let's keep the existing flow for races/stats to minimize breakage but use store for translations.

    // We can rely on the store for skills and translations
    stats.value = store.stats.stats || (await api.getStats()).data.stats
    skillsData.value = store.skills

    // Fetch sex bonuses
    try {
      const bonuses = await api.getSexBonuses()
      sexBonuses.value = bonuses.data
    } catch (e) {
      console.error('Failed to fetch sex bonuses', e)
    }

    // Initialize stats
    if (stats.value) {
      Object.keys(stats.value).forEach(key => {
        form.stats[key] = 10
      })
      calculateTotalStats()
    }

    // Initialize skills
    initializeSkills()

    // Fetch stats creation rules
    try {
      const statsRulesRes = await api.getStatsCreationRules()
      statsRules.value = statsRulesRes.data

      // Initialize stats with base value from rules or default 8
      if (stats.value && statsRules.value) {
        const startVal = statsRules.value.start_value || 8
        Object.keys(stats.value).forEach(key => {
          // Only set default if NOT editing (populate later if editing)
          if (!isEditing.value) {
            form.stats[key] = startVal
          }
        })
        // Recalculate spent points logic will be reactive
      }
    } catch (e) {
      console.error('Failed to fetch stats rules', e)
    }

    // Load Character if Editing
    if (isEditing.value) {
      isInitializing.value = true
      try {
        const charRes = await api.getCharacter(characterId.value)
        const char = charRes.data.character

        form.name = char.name
        form.sex = char.sex
        // Setting race_id triggers watcher -> updateCultures
        // checking isInitializing prevents culture reset
        form.race_id = char.race

        // Wait closely for reactivity if needed, but since we prevented reset, 
        // we can set culture immediately.
        // Also manual update cultures to be safe?
        // Watcher will run. updateCultures will run. culture_id won't be reset.
        // But ensures races are loaded.

        // Ensure cultures.value is populated if for some reason watcher didn't catch or race list wasn't ready
        const selectedRace = races.value.find(r => r.id === char.race)
        if (selectedRace) {
          cultures.value = selectedRace.cultures
        }

        form.culture_id = char.culture
        form.background = char.description || '' // Backend maps description to background
        form.physical_description = char.physical_description || ''
        form.background_localized = char.description_localized || ''
        form.physical_description_localized = char.physical_description_localized || ''

        // Stats
        form.stats = { ...char.stats }

        // Skills - backend returns specific structure, we need to map it back to form structure if needed
        // Form uses [group][skill] = point_spent

        // Backend returns:
        // skills: { "combat": { "sword": 5 }, "general": { "spot": 2 } }
        // This represents TOTAL value (base + spent + bonuses?) or just ranks?
        // The backend `Character` model stores `skills` as "Character trained skills".

        // Wait, does the backend store 'points spent' or 'final value'?
        // In creation/update logic:
        // existing_character.skills = Skills(**request.skills)

        // If the backend stores the final value, we need to reverse engineer 'points spent' 
        // by subtracting bonuses?

        // Looking at `Character` model:
        // skills: Skills = Field(..., description="Character trained skills")

        // Looking at `update_character` validation:
        // It just updates the dict.

        // Looking at `calculate_bonuses` in backend...
        // Actually, for stats and skills, the `Character` object seems to hold the values that were sent.
        // If the UI sends "points spent", then `Character` holds "points spent".

        // But let's check what `api.getCharacter` returns.
        // It returns `Character` model dump.

        // If I created a character with 5 points in Sword, and race gives +1:
        // Does DB store 5 or 6?

        // In `back/routers/creation.py`: `create_character`
        // character = Character(...)
        // It uses the payload directly.

        // So if UI sends "points spent", DB stores "points spent".
        // AND the UI calculates display value by adding bonuses.

        // So we can directly assign `char.skills` to `form.skills`?
        // `form.skills` is `Record<string, Record<string, number>>`.
        // `char.skills` structure matches.

        if (char.skills) {
          // Deep copy to avoid reactivity issues
          form.skills = JSON.parse(JSON.stringify(char.skills))
        }

        calculateTotalStats()
        calculateSpentPoints()

      } catch (e) {
        console.error("Failed to load character for editing", e)
        router.push('/characters')
      } finally {
        // Allow reactivity to settle, then disable init mode
        // Use nextTick to ensure watchers triggered by data changes (race_id) have fired
        // before we re-enable the reset logic.
        await nextTick()
        isInitializing.value = false
      }
    }

  } catch (error) {
    console.error('Error loading creation data:', error)
  } finally {
    loading.value = false
  }
})

const statsRules = ref<any>(null)

const getStatCost = (val: number) => {
  if (!statsRules.value?.costs) return 0
  // Handle both string and number keys safely
  return statsRules.value.costs[val] ?? statsRules.value.costs[String(val)] ?? 0
}

const spentStatPoints = computed(() => {
  let total = 0
  // const startVal = statsRules.value?.start_value || 8

  Object.values(form.stats).forEach(val => {
    total += getStatCost(val)
  })
  return total
})

const remainingStatPoints = computed(() => {
  const budget = statsRules.value?.budget || 27
  return budget - spentStatPoints.value
})

const maxStatLimit = computed(() => {
  if (statsRules.value?.costs) {
    const keys = Object.keys(statsRules.value.costs).map(Number)
    return Math.max(...keys)
  }
  return 18
})

const canIncreaseStat = (currentVal: number) => {
  if (!statsRules.value) return false
  const nextVal = currentVal + 1
  const currentCost = getStatCost(currentVal)
  const nextCost = getStatCost(nextVal)
  const costDiff = nextCost - currentCost

  // Protective check for costs presence
  const costs = statsRules.value.costs || {}

  // If nextVal is not in costs table, maybe we can't go there
  if (costs[nextVal] === undefined && costs[String(nextVal)] === undefined) {
    // If we are below the implicit max logic (15?), maybe fallback?
    // But if we have no cost for it, we assume it's not allowed in Point Buy
    return false
  }

  return remainingStatPoints.value >= costDiff
}




const isInitializing = ref(false)

const updateCultures = () => {
  const selectedRace = races.value.find(r => r.id === form.race_id)
  cultures.value = selectedRace ? selectedRace.cultures : []

  // Do not reset culture if we are initializing (loading existing character)
  if (!isInitializing.value) {
    form.culture_id = ''
  }
}

const createRandom = async () => {
  loading.value = true
  try {
    await api.createRandomCharacter()
    router.push('/new-game')
  } catch (error) {
    console.error('Error creating random character:', error)
  } finally {
    loading.value = false
  }
}

const generateDetails = async () => {
  if (!form.race_id || !form.culture_id || !form.sex) return
  generatingDetails.value = true
  try {
    const res = await api.generateCharacterDetails(form.race_id, form.culture_id, form.sex)
    const { name, background, physical_description, background_localized, physical_description_localized } = res.data
    form.name = name
    form.background = background
    form.physical_description = physical_description

    // If localized versions are provided, use them
    if (background_localized) form.background_localized = background_localized
    if (physical_description_localized) form.physical_description_localized = physical_description_localized
  } catch (error) {
    console.error('Error generating details:', error)
  } finally {
    generatingDetails.value = false
  }
}

const randomizeStat = (key: string) => {
  // Logic for single stat random?
  // If we randomize one, we break the total balance potentially.
  // For now, let's just randomize 3-18 range but ensure we respect total?
  // It's hard to respect total if we change just one.
  // Maybe disable single random if strict mode?
  // As per requirement "max total amount... must not be superior", so we can just set it and let the total update.
  // The user will have to adjust others if they go over.
  form.stats[key] = Math.floor(Math.random() * 16) + 3 // 3-18
  calculateTotalStats()
}

const updateStat = (key: string, delta: number) => {
  const current = form.stats[key] || 0
  const newValue = current + delta

  if (delta > 0) {
    if (!canIncreaseStat(current)) return
  }

  // Check bounds based on rules if available, else 3-18
  const min = statsRules.value?.start_value || 3
  // Max is highest key in costs or 18
  let maxVal = 18
  if (statsRules.value?.costs) {
    const keys = Object.keys(statsRules.value.costs).map(Number)
    maxVal = Math.max(...keys)
  }

  if (newValue >= min && newValue <= maxVal) {
    form.stats[key] = newValue
    calculateTotalStats()
  }
}

const totalStats = ref(0)
const calculateTotalStats = () => {
  totalStats.value = Object.values(form.stats).reduce((acc, val) => acc + val, 0)
}

const maxSkillPoints = computed(() => {
  let total = skillsData.value?.skill_creation_rules?.max_points || 40
  if (form.race_id && form.culture_id) {
    const selectedRace = races.value.find(r => r.id === form.race_id)
    const selectedCulture = selectedRace?.cultures.find(c => c.id === form.culture_id)
    if (selectedCulture?.free_skill_points) {
      total += selectedCulture.free_skill_points
    }
  }
  return total
})
const spentSkillPoints = ref(0)

// Global limit 40 points
const canIncreaseSkill = (group: string, skill: string) => {
  // Global limit 40 points
  if (spentSkillPoints.value >= maxSkillPoints.value) return false
  return true
}

const updateSkill = (group: string, skill: string, delta: number) => {
  const current = form.skills[group]?.[skill] || 0
  if (delta > 0 && !canIncreaseSkill(group, skill)) return
  if (delta < 0 && current <= 0) return

  if (!form.skills[group]) form.skills[group] = {}
  form.skills[group][skill] = current + delta
  calculateSpentPoints()
}

const calculateSpentPoints = () => {
  let total = 0
  Object.values(form.skills).forEach(group => {
    Object.values(group).forEach(val => {
      total += val
    })
  })
  spentSkillPoints.value = total
}

const initializeSkills = () => {
  // Reset key but preserve user spent points? 
  // Requirement allows for full reset or smart update. 
  // Let's reset for safety to ensure consistency with race/stat changes as per previous logic.
  form.skills = {}

  if (!skillsData.value) return

  // 1. Initialize empty skills
  if (skillsData.value?.skill_groups) {
    if (!activeSkillGroup.value) {
      const keys = Object.keys(skillsData.value.skill_groups)
      if (keys.length > 0 && keys[0]) {
        activeSkillGroup.value = keys[0]
      }
    }
    Object.entries(skillsData.value.skill_groups).forEach(([groupKey, group]: [string, any]) => {
      form.skills[groupKey] = {}
      Object.keys(group.skills).forEach(skillKey => {
        if (form.skills[groupKey]) {
          form.skills[groupKey][skillKey] = 0 // Base value
        }
      })
    })
  }

  // 2. Bonuses are now calculated dynamically for display and not added to form.skills (user points)
  // This prevents them from counting towards the spent limit.


  calculateSpentPoints()
}

// Watchers
watch(() => form.race_id, () => {
  updateCultures()
  initializeSkills()
})

// Deep watch on stats to re-calc bonuses
watch(() => form.stats, () => {
  initializeSkills()
}, { deep: true })

// Removed getTotalSkillValue as it is now redundant (value in form IS the total)
const getTotalSkillValue = (group: string, skillId: string) => {
  return form.skills[group]?.[skillId] || 0
}

const submitForm = async () => {
  loading.value = true
  try {
    // Auto-translate localized fields is now handled by backend on create

    const finalForm = JSON.parse(JSON.stringify(form))
    // We need to ensure we send the correct structure. 
    // The API expects 'stats' and 'skills'.
    // We might need to handle empty skills or specific structure if the API requires it.
    // Assuming backend handles the provided structure.

    if (isEditing.value) {
      finalForm.character_id = characterId.value
      await api.updateCharacter(finalForm)
      router.push({ name: 'character-sheet', params: { id: characterId.value } })
    } else {
      await api.createCharacter(finalForm)
      router.push('/new-game')
    }
  } catch (error) {
    console.error('Error creating/updating character:', error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8 min-h-screen pb-12">
    <div class="flex items-center gap-4">
      <router-link :to="isEditing ? `/characters/${characterId}` : '/'" class="text-gray-400 hover:text-white">
        <ChevronLeft :size="24" />
      </router-link>
      <h1 class="text-3xl font-sans font-bold text-fantasy-gold">
        {{ isEditing ? 'Modifier le Personnage' : $t('ui.create_character') }}
      </h1>
    </div>

    <div class="flex flex-col gap-12">
      <!-- Manual Creation Form -->
      <div class="bg-fantasy-secondary p-6 rounded-lg border border-gray-700 space-y-6">
        <h2 class="text-xl font-bold text-fantasy-text border-b border-gray-700 pb-2">
          {{ isEditing ? 'Modification' : $t('ui.manual_creation') }}
        </h2>

        <div class="space-y-4">
          <!-- Identity Generation -->
          <div class="flex justify-between items-center">
            <h3 class="font-medium text-fantasy-gold">{{ $t('ui.identity') }}</h3>
            <button @click="generateDetails"
              :disabled="generatingDetails || !form.race_id || !form.culture_id || isEditing"
              class="text-xs bg-fantasy-accent hover:bg-red-600 px-3 py-1 rounded flex items-center gap-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              <Sparkles v-if="!generatingDetails" :size="14" />
              <span v-else
                class="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full"></span>
              {{ generatingDetails ? $t('ui.generating') : $t('ui.generate_details') }}
            </button>
          </div>

          <div>
            <label class="block text-sm font-medium text-fantasy-muted mb-1">{{ $t('ui.name') }}</label>
            <input v-model="form.name" type="text"
              class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:border-fantasy-accent focus:outline-none"
              :placeholder="$t('ui.enterName')">
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-fantasy-muted mb-1">{{ $t('ui.sex') }}</label>
              <select v-model="form.sex" :disabled="isEditing"
                class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed">
                <option value="" disabled>{{ $t('ui.select') }}</option>
                <option value="male">{{ $t('ui.male') }}</option>
                <option value="female">{{ $t('ui.female') }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-fantasy-muted mb-1">{{ $t('ui.race') }}</label>
              <select v-model="form.race_id" @change="updateCultures" :disabled="isEditing"
                class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed">
                <option value="" disabled>{{ $t('ui.select') }}</option>
                <option v-for="race in races" :key="race.id" :value="race.id">{{ store.translate(race.id, 'races') ||
                  race.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-fantasy-muted mb-1">{{ $t('ui.culture') }}</label>
              <select v-model="form.culture_id" :disabled="!form.race_id || isEditing"
                class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed">
                <option value="" disabled>{{ $t('ui.select') }}</option>
                <option v-for="culture in cultures" :key="culture.id" :value="culture.id">{{ store.translate(culture.id,
                  'cultures') || culture.name }}</option>
              </select>
            </div>
          </div>

          <!-- Bonuses Display -->
          <div v-if="form.race_id" class="bg-fantasy-dark p-4 rounded border border-gray-700 text-sm space-y-3">
            <h4 class="font-bold text-fantasy-gold flex items-center gap-2">
              <Sparkles :size="16" />
              {{ $t('ui.bonuses_and_traits') }}
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Race Bonuses -->
              <div>
                <span class="text-xs text-fantasy-muted uppercase tracking-wider font-bold mb-1 block">Race ({{
                  store.translate(form.race_id, 'races') || races.find(r => r.id === form.race_id)?.name}})</span>
                <ul class="space-y-1">
                  <li v-for="(bonus, stat) in races.find(r => r.id === form.race_id)?.characteristic_bonuses"
                    :key="stat" class="text-blue-300">
                    +{{ bonus }} {{ store.translate(String(stat), 'stats') }}
                  </li>
                  <li v-if="races.find(r => r.id === form.race_id)?.base_languages" class="text-gray-300">
                    <span class="text-fantasy-muted">{{ $t('ui.languages') }}:</span> {{races.find(r => r.id ===
                      form.race_id)?.base_languages.join(', ')}}
                  </li>
                </ul>
              </div>

              <!-- Culture Bonuses -->
              <div v-if="form.culture_id">
                <span class="text-xs text-fantasy-muted uppercase tracking-wider font-bold mb-1 block">Culture ({{
                  store.translate(form.culture_id, 'cultures') || cultures.find(c => c.id === form.culture_id)?.name
                }})</span>
                <ul class="space-y-1">
                  <li
                    v-for="(bonus, skill) in races.find(r => r.id === form.race_id)?.cultures.find(c => c.id === form.culture_id)?.skill_bonuses"
                    :key="skill" class="text-green-300">
                    +{{ bonus }} {{ store.translate(String(skill), 'skills') }}
                  </li>
                  <li
                    v-if="races.find(r => r.id === form.race_id)?.cultures.find(c => c.id === form.culture_id)?.traits"
                    class="text-fantasy-gold italic">
                    "{{store.translate(races.find(r => r.id === form.race_id)?.cultures.find(c => c.id ===
                      form.culture_id)?.traits || '', 'traits')}}"
                  </li>
                </ul>
              </div>

              <!-- Sex Bonuses -->
              <div v-if="form.sex && sexBonuses[form.sex]">
                <span class="text-xs text-fantasy-muted uppercase tracking-wider font-bold mb-1 block">Sexe ({{
                  $t(`ui.${form.sex}`) }})</span>
                <ul class="space-y-1">
                  <!-- Stats -->
                  <li v-for="(bonus, stat) in sexBonuses[form.sex].stats" :key="stat" class="text-blue-300">
                    +{{ bonus }} {{ store.translate(String(stat), 'stats') }}
                  </li>
                  <!-- Skills -->
                  <li v-for="(bonus, skill) in sexBonuses[form.sex].skills" :key="skill" class="text-green-300">
                    +{{ bonus }} {{ store.translate(String(skill), 'skills') }}
                  </li>
                </ul>
              </div>

            </div>
          </div>

          <div>
            <div class="flex justify-between items-end mb-2">
              <label class="block text-sm font-medium text-fantasy-muted">{{ $t('ui.statistics_header') }}</label>
              <div class="flex flex-col items-end">
                <span class="text-xs text-fantasy-muted italic">{{ $t('ui.stat_range') }} : {{ statsRules?.start_value
                  || 3 }} - {{ maxStatLimit }} (Start: {{
                    statsRules?.start_value || 8 }})</span>
                <span class="text-xs font-bold" :class="remainingStatPoints < 0 ? 'text-red-500' : 'text-fantasy-gold'">
                  <!-- {{ $t('ui.total') }}: {{ totalStats }} / 60 -->
                  {{ $t('ui.evolution_points') }}: {{ remainingStatPoints }} / {{ statsRules?.budget || 27 }}
                </span>
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div v-for="(statInfo, key) in stats" :key="key"
                class="grid grid-cols-[1fr_auto] items-center gap-2 bg-fantasy-dark p-2 rounded border border-gray-700">
                <span class="text-sm text-fantasy-muted capitalize">{{ store.translate(String(key), 'stats') }}</span>
                <div class="flex items-center gap-2">
                  <button @click="updateStat(String(key), -1)"
                    class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                    :disabled="form.stats[key] <= (statsRules?.start_value || 8)">
                    <Minus :size="14" />
                  </button>
                  <div class="flex flex-col items-center w-8">
                    <span class="text-center font-bold text-fantasy-gold">{{ form.stats[key] }}</span>
                    <span class="text-[9px] text-gray-500" v-if="statsRules?.costs">Cost: {{
                      getStatCost(form.stats[key] || 0) }}</span>
                  </div>

                  <button @click="updateStat(String(key), 1)"
                    class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed group relative"
                    :disabled="!canIncreaseStat(form.stats[key] || 0)">
                    <Plus :size="14" />
                    <!-- Tooltip for cost -->
                    <span
                      class="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-black text-white text-xs px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none"
                      v-if="statsRules?.costs && form.stats[key] !== undefined && statsRules.costs[(form.stats[key] || 0) + 1] !== undefined">
                      -{{ getStatCost((form.stats[key] || 0) + 1) - getStatCost(form.stats[key] || 0) }} pts
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Skills Section -->
          <div v-if="skillsData">
            <div class="flex justify-between items-center mb-2">
              <div class="flex flex-col">
                <label class="block text-sm font-medium text-fantasy-muted">{{ $t('ui.skills') }}</label>
                <span class="text-xs text-fantasy-muted italic">{{ $t('ui.max_skill_points') }}</span>
              </div>
              <span class="text-xs font-bold"
                :class="spentSkillPoints >= maxSkillPoints ? 'text-red-400' : 'text-green-400'">
                {{ $t('ui.points_remaining') }}: {{ maxSkillPoints - spentSkillPoints }} / {{ maxSkillPoints }}
              </span>
            </div>

            <!-- Tabs Navigation -->
            <div class="flex gap-2 overflow-x-auto pb-2 mb-4 custom-scrollbar">
              <button v-for="(_, groupKey) in skillsData.skill_groups" :key="groupKey"
                @click="activeSkillGroup = String(groupKey)"
                class="px-4 py-2 rounded-full whitespace-nowrap text-sm font-medium transition-colors border"
                :class="activeSkillGroup === String(groupKey)
                  ? 'bg-fantasy-accent border-fantasy-accent text-white'
                  : 'bg-fantasy-dark border-gray-600 text-fantasy-muted hover:text-fantasy-text hover:border-gray-500'">
                {{ store.translate(String(groupKey), 'skill_groups') }}
              </button>
            </div>

            <!-- Active Group Skills -->
            <div v-if="activeSkillGroup && skillsData?.skill_groups?.[activeSkillGroup]"
              class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <div class="col-span-full">
                <!-- Removed group title as it's in the tab now, or we can keep it for clarity if needed, 
                    but usually tabs imply the title. Let's keep it clean. -->
              </div>

              <div v-for="(skill, skillKey) in skillsData.skill_groups[activeSkillGroup].skills" :key="skillKey"
                class="flex justify-between items-center bg-fantasy-dark p-2 rounded border border-gray-700 text-sm">
                <div class="flex flex-col">
                  <Tooltip :text="store.translate(String(skillKey), 'skill_descriptions')">
                    <span
                      class="text-fantasy-text underline decoration-dashed underline-offset-4 decoration-fantasy-muted/50 cursor-help">{{
                        store.translate(String(skillKey), 'skills') }}</span>
                  </Tooltip>
                  <span v-if="getRaceSkillBonus(String(skillKey)) > 0" class="text-[10px] text-fantasy-gold block">
                    +{{ getRaceSkillBonus(String(skillKey)) }} (Race)
                  </span>
                  <span v-if="getCultureSkillBonus(String(skillKey)) > 0" class="text-[10px] text-fantasy-gold block">
                    +{{ getCultureSkillBonus(String(skillKey)) }} (Culture)
                  </span>
                  <span v-if="getSexSkillBonus(String(skillKey)) > 0" class="text-[10px] text-blue-400 block">
                    +{{ getSexSkillBonus(String(skillKey)) }} (Sexe)
                  </span>
                  <span v-if="getStatBonusForSkill(String(skillKey)) > 0" class="text-[10px] text-blue-400 block">
                    +{{ getStatBonusForSkill(String(skillKey)) }} (Stat)
                  </span>
                </div>
                <div class="flex items-center gap-2">
                  <button @click="updateSkill(String(activeSkillGroup), String(skillKey), -1)"
                    class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                    :disabled="(form.skills[String(activeSkillGroup)]?.[String(skillKey)] || 0) <= 0">
                    <Minus :size="14" />
                  </button>
                  <span class="w-6 text-center font-bold"
                    :class="(form.skills[String(activeSkillGroup)]?.[String(skillKey)] || 0) > 0 ? 'text-fantasy-gold' : 'text-gray-500'">
                    {{ (form.skills[String(activeSkillGroup)]?.[String(skillKey)] || 0) +
                      getRaceSkillBonus(String(skillKey)) + getCultureSkillBonus(String(skillKey)) +
                      getSexSkillBonus(String(skillKey)) + getStatBonusForSkill(String(skillKey)) }}
                  </span>
                  <button @click="updateSkill(String(activeSkillGroup), String(skillKey), 1)"
                    class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                    :disabled="spentSkillPoints >= maxSkillPoints">
                    <Plus :size="14" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-fantasy-muted mb-1">{{ $t('ui.physical_description') }}</label>
          <textarea v-if="form.physical_description_localized" v-model="form.physical_description_localized" rows="2"
            class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:outline-none placeholder-gray-500"
            :placeholder="$t('ui.localized_physical_description_placeholder')"></textarea>
          <textarea v-else v-model="form.physical_description" rows="2"
            class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:outline-none"></textarea>

          <!-- Hidden field if localized is active to keep original english value for system -->
          <input v-if="form.physical_description_localized" type="hidden" v-model="form.physical_description">
        </div>

        <div>
          <label class="block text-sm font-medium text-fantasy-muted mb-1">{{ $t('ui.history') }}</label>
          <textarea v-if="form.background_localized" v-model="form.background_localized" rows="3"
            class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:outline-none placeholder-gray-500"
            :placeholder="$t('ui.localized_history_placeholder')"></textarea>
          <textarea v-else v-model="form.background" rows="3"
            class="w-full bg-fantasy-dark border border-gray-600 rounded px-3 py-2 text-fantasy-text focus:border-fantasy-accent focus:outline-none"></textarea>

          <!-- Hidden field if localized is active -->
          <input v-if="form.background_localized" type="hidden" v-model="form.background">
        </div>

        <button @click="submitForm" :disabled="loading"
          class="w-full bg-fantasy-accent hover:bg-red-600 text-white font-bold py-3 rounded flex justify-center items-center gap-2 transition-colors disabled:opacity-50 cursor-pointer">
          <Save :size="20" />
          {{ $t('ui.create_character_button') }}
        </button>
      </div>
    </div>

    <!-- Random Creation -->
    <div v-if="!isEditing" class="space-y-6">
      <div class="bg-fantasy-secondary p-6 rounded-lg border border-gray-700 text-center space-y-4">
        <h2 class="text-xl font-bold text-fantasy-text">{{ $t('ui.let_fate_decide') }}</h2>
        <p class="text-fantasy-muted">{{ $t('ui.random_generation_description') }}</p>
        <button @click="createRandom" :disabled="loading"
          class="w-full bg-fantasy-gold text-gray-900 hover:bg-yellow-400 font-bold py-4 rounded flex justify-center items-center gap-2 transition-colors disabled:opacity-50 cursor-pointer">
          <span v-if="loading"
            class="animate-spin h-6 w-6 border-2 border-gray-900 border-t-transparent rounded-full"></span>
          <Dices v-else :size="24" />
          {{ loading ? $t('ui.generating_random') : $t('ui.random_generation_button') }}
        </button>
      </div>

      <div class="bg-fantasy-secondary p-6 rounded-lg border border-gray-700">
        <h3 class="text-lg font-bold text-fantasy-text mb-2">{{ $t('ui.creation_tips_title') }}</h3>
        <ul class="list-disc list-inside text-fantasy-muted space-y-2 text-sm">
          <li>Les Humains sont polyvalents et ambitieux.</li>
          <li>Les Elfes excellent dans la magie et la perception.</li>
          <li>Les Nains sont robustes et maîtres artisans.</li>
          <li>Les Hobbits sont discrets et chanceux.</li>
        </ul>
      </div>
    </div>

  </div>
</template>
