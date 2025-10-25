<script setup lang="ts">
import StoryFlow from '@/components/story/StoryFlow.vue'
</script>

<template>
  <v-app>
    <v-app-bar color="primary">
      <v-app-bar-title>WebTangl v3.7</v-app-bar-title>
    </v-app-bar>

    <v-main>
      <v-container>
        <StoryFlow />
      </v-container>
    </v-main>
  </v-app>
</template>
