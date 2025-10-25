<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { StoryStatus } from '@/types'

import { useGlobal } from "@/globals";
const { $http, $debug, $verbose } = useGlobal()

const status = ref<StoryStatus | null>(null)

const getStatus = (async () => {
  try {
    const response = await $http.value.get('/story/status')
    status.value = response.data
  } catch (error) {
    console.error(error)
  }
})

const getItemStyle = (item) => {
  const defaultStyle = {
    'color': 'gray',
    'min-height': '12px',
    'padding': '2px',
  }
  return {
    ... defaultStyle,
    ... item.style
  }
}

const getItemText = (item) => {
  if (item.value) {
    return item.key + ": " + item.value
  }
  return item.key
}

onMounted( () => {
  getStatus()
})

</script>

<template>

  <v-card flat>
    <v-card-title class="subtitle text-center pt-5" style="font-size: 1.0rem">
      Status
    </v-card-title>
    <v-card-item class="pa-2">
      <v-list density="compact" class="pa-0 ma-0">
        <v-list-item v-for="(item, i) in status"
                     :key="i"
                     :style=getItemStyle(item)
                     :subtitle=getItemText(item)>
          <template v-slot:prepend>
            <v-icon v-if="'icon' in item" class="mr-1" size="x-small">mdi-{{ item.icon }}</v-icon>
          </template>
        </v-list-item>
      </v-list>
    </v-card-item>
  </v-card>

  <v-card v-if="$debug && $verbose" flat>
    <v-card-item border class="pa-2">
      <v-card border class="text-caption pl-1" style="line-height: 1rem">
        <v-card-item class="pa-0 ma-1">Status: {{ status }}</v-card-item>
      </v-card>
    </v-card-item>
  </v-card>

</template>
