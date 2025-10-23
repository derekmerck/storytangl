<script setup lang="ts">

import {StyledJournalItem, JournalMediaItems} from "@/types";

const props = defineProps({
  dialog_block: {
    type: Object as () => StyledJournalItem,
    required: true,
  }
})

const getDialogStyle = (dialog_block: StyledJournalItem) => {
  if (dialog_block?.label) {
    const bg = {'background-color': "rgb(0,0,0,0.2)"}
    if (dialog_block?.style_dict) {
      return { ... dialog_block.style_dict, ... bg }
    }
    return bg }
  else {
    return dialog_block.style_dict
  }
}

</script>

<template>
  <v-col cols="12" class="py-1">
    <v-card-text v-if="!dialog_block?.label" v-html="dialog_block.text"/>

    <v-card v-if="dialog_block?.label"
            class="pa-0 d-flex overflow-visible"
            :style="getDialogStyle(dialog_block)"
    >
      <v-avatar v-if="dialog_block.media_dict?.avatar_im"
                  rounded="0"
                  size="64"
                  class="mr-2">
          <v-img :src="dialog_block.media_dict.avatar_im.url"/>
      </v-avatar>
      <v-card-text
            v-html="dialog_block.text"
            class="py-1 rounded-lg d-flex align-center"/>
<!--      <v-badge v-if="dialog_block?.label"-->
<!--               size="small"-->
<!--               class="mr-10"-->
<!--               color="red"-->
<!--               :content="dialog_block.label" floating="true"></v-badge>-->

    </v-card>

  </v-col>
</template>