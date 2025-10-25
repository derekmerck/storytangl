<script setup lang="ts">
import {onMounted, ref} from 'vue'
import Status from "@/components/StoryStatus.vue";
import StoryFlow from "@/components/story/StoryFlow.vue";
import Navbar from "@/components/navbar/AppNavbar.vue";
import Footer from "@/components/AppFooter.vue"
import { useStore } from "@/store"
import * as process from "process";

const drawer = ref(null)

// const store = useStore()

// const setupUser = () => {
//   const user_secret =
//   console.log('secret', user_secret)
//   const user_api_key = "ABCDEFG"
//   store.$patch( {
//     user_secret: user_secret,
//     user_api_key: user_api_key
//   })
// }

// onMounted( () => {
//   setupUser()
// })

// import { reactive } from 'vue';
// const state = reactive({
//   loading: true
// });

</script>

<template>
  <v-app id="webtangl">

    <Navbar v-on:toggle-drawer="drawer = !drawer"/>

    <v-navigation-drawer v-model="drawer" :permanent=true width="170">
      <Status />
    </v-navigation-drawer>

    <v-main>
      <v-container >
      <StoryFlow/>
      <Footer />
      </v-container>
    </v-main>


  </v-app>
</template>

<style lang="scss">
//@import "style.css";
// Burnaby Stencil from Adobe
// Tenby from Adobe
@import url('https://use.typekit.net/isd6uld.css');

.title {
  font-size: 2rem !important;
  text-transform: uppercase !important;
  font-family: burnaby-stencil, sans-serif;
  font-weight: 400;
  font-style: normal;
  color: rgb(var(--v-theme-primary));
  opacity: 0.9;
}

.subtitle {
  //@extend .title;
  //font-size: 1.3rem;
  //font-variant: small-caps;
  //text-transform: uppercase !important;
  color: rgb(var(--v-theme-primary)) !important;
  opacity: 0.8;
}

//p {
//  margin-top: 0.6rem;
//  margin-bottom: 0.6rem;
//}

.brand {
  color: rgb(var(--v-theme-primary));
  fill: rgb(var(--v-theme-primary));
}

.text-caption {
  font-size: 0.7em !important;
  color: rgba(255, 255, 255, 0.40) !important;
}

.text-center {
  text-align: center !important;
}

:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;

  color-scheme: light dark;
  color: rgba(255, 255, 255, 0.87);
  background-color: #242424;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  -webkit-text-size-adjust: 100%;
}

</style>