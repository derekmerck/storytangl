<script setup lang="ts">
import StoryAction from "./StoryAction.vue";
import {JournalStoryUpdate} from "@/types"

import { useGlobal } from "@/globals";
import StoryDialogBlock from "@/components/story/StoryDialogBlock.vue"
const { $debug, $verbose } = useGlobal()

// The block prop received from parent
const props = defineProps({
  block: {
    type: Object as () => JournalStoryUpdate,
    required: true,
  }
})

const emit = defineEmits(['doAction'])

// Pass-up emitted 'doAction' event when an action button is clicked
const doAction = (action, action_uid, passback) => {
  emit('doAction', action, action_uid, passback)
}

const hasImage = () => {
  return props.block?.media_dict?.narrative_im !== undefined
}

const hasLandscapeImage = () => {
  return props.block?.media_dict?.narrative_im?.orientation === "landscape"
}

const hasPortraitImage = () => {
  return props.block?.media_dict?.narrative_im?.orientation === "portrait"
}

</script>

<template>

  <v-card>

    <v-card-item v-if="hasLandscapeImage()" class="mx-5 mt-5">
      <v-parallax :src="block.media_dict?.narrative_im.url" cover height="50vh" scale="0.5" />
    </v-card-item>

    <v-card-title v-if="'title' in block" class="subtitle mx-5 mt-5">
      {{ block.title }}
    </v-card-title>

    <v-card-item>
      <v-row align="center" justify="center">

        <v-col>
          <v-card-text v-if="!block?.dialog"
                       v-html="block.text"></v-card-text>

          <v-row v-if="block?.dialog"
                 v-for="db in block.dialog">
            <StoryDialogBlock :dialog_block="db"/>
          </v-row>

          <v-row>
            <v-col>
              <v-card-actions v-if="'actions' in block">
                <v-row dense>
                <StoryAction v-for="action in block.actions"
                             :action="action"
                             :key="action.uid"
                             v-bind="$attrs"
                             @doAction="doAction" />
                </v-row>
              </v-card-actions>
            </v-col>
          </v-row>
        </v-col>

        <v-col v-if="hasImage() && !hasLandscapeImage()" cols="12" :md="(hasPortraitImage()) ? '4' : '5'" class="mr-5" order="first" order-md="last">
          <v-img :src="block.media_dict?.narrative_im.url" :style="{ maxHeight: '70vh' }"></v-img>
        </v-col>

      </v-row>
    </v-card-item>

    <v-card-item v-if="$debug && $verbose">
      <v-card border>
        <v-card-text class="text-caption">Block: {{ block }}</v-card-text>
      </v-card>
    </v-card-item>

  </v-card>

</template>
