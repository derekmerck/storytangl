<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useDisplay } from 'vuetify'

import AppNavbar from '@/components/AppNavbar.vue'
import AppFooter from '@/components/AppFooter.vue'
import StoryStatus from '@/components/StoryStatus.vue'
import StoryFlow from '@/components/story/StoryFlow.vue'
import { useStore } from '@/store'

const drawer = ref(true)
const store = useStore()
const display = useDisplay()

const isDesktop = computed(() => display.mdAndUp.value)

onMounted(async () => {
  drawer.value = isDesktop.value

  if (store.user_secret) {
    try {
      await store.getApiKey()
    } catch (error) {
      console.error('Failed to initialize authentication:', error)
    }
  }
})

const toggleDrawer = () => {
  drawer.value = !drawer.value
}
</script>

<template>
  <v-app id="webtangl">
    <AppNavbar @toggle-drawer="toggleDrawer" />

    <v-navigation-drawer
      v-model="drawer"
      :permanent="isDesktop"
      width="260"
      border="0"
    >
      <v-list density="compact">
        <v-list-item>
          <v-list-item-title class="text-h6">Status</v-list-item-title>
        </v-list-item>
      </v-list>
      <v-divider class="mb-2" />
      <StoryStatus />
    </v-navigation-drawer>

    <v-main>
      <v-container class="py-6" fluid>
        <v-row justify="center">
          <v-col cols="12" lg="9">
            <StoryFlow />
          </v-col>
        </v-row>
        <AppFooter />
      </v-container>
    </v-main>
  </v-app>
</template>
