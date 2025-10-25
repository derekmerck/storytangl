<script setup type="ts">
import { ref, computed, watch } from "vue";
import axios from "axios";

const dialog_open = ref(false)

const old_api_url = computed(() => axios.defaults.baseURL)
const new_api_url = ref(null)

const saveApiUrl = () => {
  // Handle saving the secret here
  if (new_api_url != '') {
    console.log('new api url', new_api_url.value);
    axios.defaults.baseURL = new_api_url.value;
  }
}

const emit = defineEmits(['close_dialog'])

watch(dialog_open, (newValue) => {
  if (newValue === false)
  {
    emit('close_dialog');
  }
});

</script>

<template>
  <v-dialog activator="parent"
            v-model="dialog_open"
            max-width="65%"
            max-height="85%">
  <v-card>
    <v-card-title>
      <span class="text-h5">Set Game Host</span>
    </v-card-title>
    <v-card-item>
      <v-text-field
          label="Enter the API url"
          v-model.trim="new_api_url"
          :placeholder="old_api_url"
          hint="Reference API often available at: https://app.storytan.gl/api/v2"
          :persistent-placeholder=true
      ></v-text-field>
    </v-card-item>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn color="primary" @click="dialog_open = false">
        Cancel
      </v-btn>
      <v-btn color="primary" @click="saveApiUrl(); dialog_open = false" id="saveApiUrl">
        Save API url
      </v-btn>
    </v-card-actions>
  </v-card>
  </v-dialog>
</template>