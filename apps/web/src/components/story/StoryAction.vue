<script setup lang="ts">

// The choice prop received from parent
import { JournalAction } from "@/types";

const props = defineProps({
  action: {
    type: Object as () => JournalAction,
    required: true,
  }
})

const emit = defineEmits(['doAction'])

</script>

<template>
  <v-col>
    <v-btn :key="action.uid"
        @click="emit('doAction', action.uid, action.payload)"
        size="small">
      <v-icon :icon="'mdi-' + (action.icon || 'vuetify')" class="text-primary-lighten-2"></v-icon>
      {{ action.text }}
    </v-btn>
  </v-col>
</template>
