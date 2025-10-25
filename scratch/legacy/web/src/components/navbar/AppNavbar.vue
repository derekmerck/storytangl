
<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import axios from "axios";
import { WorldList } from "@/types";
import { useStore } from '@/store'
import WorldInfo from "./WorldInfo.vue";
import SecretDialog from "./SecretDialog.vue";
import ApiDialog from "./ApiDialog.vue";
import SystemInfo from "./SystemInfo.vue";

const store = useStore()
const worlds = ref<WorldList>([])
// Fetch your worlds list from the API

const user_menu_active = ref(false)
const info_menu_active = ref(false)
// todo: this shuld be system-info guide_url
const guideUrl = ref<string | null>('/guide');

import { useGlobal } from "@/globals";
const { $http, $debug, $verbose, remapURL } = useGlobal()

const openGuide = () => {
  if (guideUrl.value) {
    const url = remapURL( guideUrl.value );
    window.open(url, 'StoryTangl User Guide');
  }
};

onMounted(async () => {

  if (store.current_world_info === undefined) {
    store.getCurrentWorldInfo()
  }

  try {
    const response = await axios.get<WorldList>('/system/worlds')
    worlds.value = response.data
  } catch(error) {
    console.error(error)
  }
})

const selectWorld = async (world_id) => {
  // Implement your logic here
  try {
    const response = await axios.put('/user/world', world_id)
    store.setCurrentWorld( world_id )
  } catch (error) {
    console.error(error)
  }
}

</script>

<template>
  <v-app-bar >
    <v-app-bar-nav-icon @click.stop="$emit('toggle-drawer')">
      <v-icon>mdi-menu</v-icon>
    </v-app-bar-nav-icon>

    <v-app-bar-title class="brand title">
      WebTangl
    </v-app-bar-title>

    <v-spacer></v-spacer>

    <v-menu id="worldsMenu">
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" dark>
          Worlds
        </v-btn>
      </template>
      <v-list>
        <v-list-item
            v-for="(world, index) in worlds"
            :key="index"
            :value="index"
            @click="selectWorld(world.key)"
        >
          <v-list-item-title :style=world.style>{{ world.value }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <!-- User Options Dropdown -->
    <v-menu offset-y v-model="user_menu_active" id="userMenu">
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" dark>
          User
        </v-btn>
      </template>

      <v-list>
        <v-list-item @click="">
          Set Secret
          <SecretDialog @close_dialog="user_menu_active = false"></SecretDialog>
        </v-list-item>

        <v-list-item @click="">
          Set Game Host
          <ApiDialog @close_dialog="user_menu_active = false"></ApiDialog>
        </v-list-item>

      </v-list>
    </v-menu>

    <!-- Info Options Dropdown -->
    <v-menu offset-y v-model="info_menu_active" id="infoMenu">
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" dark>
          Info
        </v-btn>
      </template>

      <v-list>
        <v-list-item @click="">
          World
          <WorldInfo @close_dialog="info_menu_active = false"></WorldInfo>
        </v-list-item>

        <v-list-item @click="">
          System
          <SystemInfo @close_dialog="info_menu_active = false"></SystemInfo>
        </v-list-item>

        <v-list-item @click="openGuide" :disabled="!guideUrl">
          Guide
        </v-list-item>

      </v-list>
    </v-menu>


  </v-app-bar>
</template>

