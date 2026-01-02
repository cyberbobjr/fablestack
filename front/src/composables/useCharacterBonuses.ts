import { computed, type Ref } from 'vue'
import { useGameDataStore } from '../stores/gameData'

export function useCharacterBonuses(
    raceId: Ref<string | undefined>,
    cultureId: Ref<string | undefined>,
    sex: Ref<string | undefined>,
    stats: Ref<Record<string, number>>,
    sexBonuses: Ref<Record<string, any>>
) {
    const gameDataStore = useGameDataStore()

    // --- Helpers to get Data ---
    const raceData = computed(() => {
        if (!raceId.value || !gameDataStore.races) return null
        return gameDataStore.races.find(r => r.id === raceId.value)
    })

    const cultureData = computed(() => {
        const race = raceData.value
        if (!race || !cultureId.value) return null
        return race.cultures.find(c => c.id === cultureId.value)
    })

    const sexBonusData = computed(() => {
        if (!sex.value || !sexBonuses.value) return null
        return sexBonuses.value[sex.value]
    })

    // --- Stat Bonuses ---

    const getRaceStatBonus = (statKey: string) => {
        // Typically race itself doesn't have stat bonuses in this system (usually culture), 
        // but we check if the schema allows it.
        return (raceData.value as any)?.stats?.[statKey] || 0
    }

    const getCultureStatBonus = (statKey: string) => {
        return (cultureData.value as any)?.stats?.[statKey] || 0
    }

    const getSexStatBonus = (statKey: string) => {
        return sexBonusData.value?.stats?.[statKey] || 0
    }

    // --- Skill Bonuses ---

    const getRaceSkillBonus = (skillKey: string) => {
        if (!gameDataStore.skills?.racial_affinities || !raceData.value?.name) return 0

        const affinities = gameDataStore.skills.racial_affinities[raceData.value.name] || []
        const affinity = affinities.find((a: any) => a.skill === skillKey)
        return affinity ? affinity.base_points : 0
    }

    const getCultureSkillBonus = (skillKey: string) => {
        return cultureData.value?.skill_bonuses?.[skillKey] || 0
    }

    const getSexSkillBonus = (skillKey: string) => {
        return sexBonusData.value?.skills?.[skillKey] || 0
    }

    const getStatBonusForSkill = (skillKey: string) => {
        if (!gameDataStore.skills?.skill_groups || !stats.value) return 0

        // Find skill definition to get stat_bonuses rules
        let skillDef: any = null
        // We have to iterate groups because we don't know the group of the skillKey easily
        // Optimally gameDataStore could have a flattened map, but we iterate for now
        for (const group of Object.values(gameDataStore.skills.skill_groups) as any[]) {
            if (group.skills[skillKey]) {
                skillDef = group.skills[skillKey]
                break
            }
        }

        if (!skillDef?.stat_bonuses) return 0

        let total = 0
        for (const [stat, bonus] of Object.entries(skillDef.stat_bonuses) as [string, any][]) {
            const statVal = stats.value[stat] || 0
            if (statVal >= bonus.min_value) {
                total += bonus.bonus_points
            }
        }
        return total
    }

    return {
        getRaceStatBonus,
        getCultureStatBonus,
        getSexStatBonus,
        getRaceSkillBonus,
        getCultureSkillBonus,
        getSexSkillBonus,
        getStatBonusForSkill
    }
}
