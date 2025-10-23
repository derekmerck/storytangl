<script setup lang="ts">
import { ref } from 'vue'

const message = ref('Hello StoryTangl!')
const count = ref(0)

function increment() {
  count.value++
}
</script>

<template>
  <v-app>
    <v-app-bar color="primary">
      <v-app-bar-title>WebTangl v3.7</v-app-bar-title>
    </v-app-bar>

    <v-main>
      <v-container>
        <v-card class="mx-auto pa-6" max-width="600">
          <v-card-title class="text-h4 mb-4">
            {{ message }}
          </v-card-title>

          <v-card-text>
            <p class="text-h6 mb-4">Environment is ready!</p>
            
            <v-row align="center" class="mb-4">
              <v-col>
                <p>Counter: {{ count }}</p>
              </v-col>
              <v-col>
                <v-btn @click="increment" color="secondary">
                  <v-icon start>mdi-plus</v-icon>
                  Increment
                </v-btn>
              </v-col>
            </v-row>

            <v-alert type="success" variant="tonal">
              <v-icon start>mdi-check-circle</v-icon>
              Vue 3, Vuetify 3, TypeScript, and Vite are all configured!
            </v-alert>
          </v-card-text>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<style scoped>
.text-h4 {
  color: rgb(var(--v-theme-primary));
}
</style>
