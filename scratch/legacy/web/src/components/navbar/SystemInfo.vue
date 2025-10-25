<script setup type="ts">
import {onMounted, ref, watch} from "vue";
import axios from "axios";
// import { SystemInfoResponse } from "@/types";
import { useGlobal } from "@/globals"
const { $http, $debug, $verbose, makeMediaDict } = useGlobal()

const system_info = ref({})
const getSystemInfo = async () => {
  const response = await $http.value.get('/system/info')
  // Check if the response data has a media list and transform it
  if(response.data && response.data.media) {
    response.data.media_dict = makeMediaDict(response.data);
  }
  system_info.value = response.data
}

const client_info = {
  version: import.meta.env.VITE_CLIENT_APP_VERSION
}

onMounted( () => {
  getSystemInfo()
})

const dialog_open = ref(false)

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
      <v-img v-if:="system_info?.media_dict?.info_im"
             :src="system_info.media_dict.info_im.url"
             max-height="350" :cover="true">
        <v-card-title class="title" style="background: rgb(0, 0, 0, 0.5)">System Info</v-card-title>
      </v-img>
      <v-card-item class="pa-0">
        <v-list density="compact">

          <v-list-item>
            <v-card-text class="py-2"> Engine: {{ system_info.engine }} {{ system_info.version }}</v-card-text>
          </v-list-item>

          <v-list-item>
            <v-card-text class="py-2"> Uptime: {{ system_info.uptime }} </v-card-text>
          </v-list-item>

          <v-list-item>
            <v-card-text class="py-2"> Client: {{ client_info.version }} </v-card-text>
          </v-list-item>

        </v-list>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="dialog_open = false">Close</v-btn>
        </v-card-actions>
      </v-card-item>

    <v-card v-if="$debug && $verbose" flat>
      <v-card-item border class="pa-2">
        <v-card border class="text-caption pl-1" style="line-height: 1rem">
          <v-card-item class="pa-0 ma-1">info: {{ system_info }}</v-card-item>
        </v-card>
      </v-card-item>
    </v-card>

    </v-card>
  </v-dialog>
</template>