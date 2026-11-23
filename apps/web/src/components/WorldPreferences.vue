<script setup lang="ts">
import { useStore } from '@/store'

/**
 * Controls for the current world's declared viewer preferences. Changing one
 * is local presentation: it re-renders bound media and never takes a story step.
 */
const store = useStore()
</script>

<template>
  <v-list v-if="store.world_preferences.length" density="compact" data-testid="world-preferences">
    <v-list-subheader>Preferences</v-list-subheader>
    <v-list-item v-for="preference in store.world_preferences" :key="preference.id">
      <v-switch
        v-if="preference.kind === 'boolean'"
        :model-value="store.preference_values[preference.id]"
        :label="preference.label"
        :hint="preference.help ?? undefined"
        :data-preference="preference.id"
        color="primary"
        density="compact"
        persistent-hint
        @update:model-value="store.setPreference(preference.id, Boolean($event))"
      />
      <template v-else>
        <div class="text-body-2">{{ preference.label }}</div>
        <v-btn-toggle
          :model-value="store.preference_values[preference.id]"
          :data-preference="preference.id"
          color="primary"
          density="compact"
          mandatory
          variant="outlined"
          @update:model-value="store.setPreference(preference.id, String($event))"
        >
          <v-btn v-for="value in preference.values" :key="value" :value="value" size="small">
            {{ value }}
          </v-btn>
        </v-btn-toggle>
        <div v-if="preference.help" class="text-caption text-medium-emphasis">
          {{ preference.help }}
        </div>
      </template>
    </v-list-item>
  </v-list>
</template>
