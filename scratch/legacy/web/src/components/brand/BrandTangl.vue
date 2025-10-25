<template>
  <v-icon class="brand" :size="this.size"><component :is=getThemeTangl() /></v-icon>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTheme } from 'vuetify'

const size = ref()

const getThemeTangl= () => {
  const theme = useTheme()
  // return theme.current._value.icons.heart
}

</script>
