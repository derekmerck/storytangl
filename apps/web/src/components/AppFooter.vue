<script setup lang="ts">
import { computed } from 'vue'

const version = computed(() => import.meta.env?.VITE_APP_VERSION ?? '3.7.0')
const year = new Date().getFullYear()
</script>

<template>
  <v-footer class="mt-8" height="64" app>
    <v-row justify="center" align="center" no-gutters>
      <v-col class="text-center text-caption" cols="12">
        WebTangl v{{ version }} • {{ year }} • Built with StoryTangl
      </v-col>
    </v-row>
  </v-footer>
</template>
