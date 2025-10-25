<script setup type="ts">
import {computed, onMounted, ref, watch} from "vue";
import { useStore } from "@/store";

const dialog_open = ref(false)

const store = useStore()
const world_info = store.current_world_info

import { useGlobal } from "@/globals"
const { makeMediaDict } = useGlobal()
const media_dict = makeMediaDict(world_info)
console.log(media_dict.info_im)

const emit = defineEmits(['close_dialog'])

watch(dialog_open, (newValue) => {
  if (newValue === false)
  {
    emit('close_dialog');
  }
});

</script>

<template>
  <!-- Info Dialog -->
  <v-dialog activator="parent"
            v-model="dialog_open"
            width="auto"
            max-width="65%"
            max-height="85%">
    <v-card>
      <v-img v-if:="media_dict?.info_im"
             :src="media_dict.info_im?.url"
             max-height="350" cover>
        <v-card-title class="title" style="background: rgb(0, 0, 0, 0.5)">{{ world_info.title }}</v-card-title>
      </v-img>
      <v-card-item class="pa-0">
        <v-list>

          <v-list-item>
            <v-card-text v-html="world_info.summary" />
          </v-list-item>

          <v-list-item>
            <v-card-text> {{ world_info.author }}, {{ world_info.date }} </v-card-text>
          </v-list-item>

        </v-list>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="dialog_open = false">Close</v-btn>
        </v-card-actions>
      </v-card-item>
    </v-card>
  </v-dialog>
</template>