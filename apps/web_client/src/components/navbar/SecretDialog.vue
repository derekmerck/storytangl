<script setup type="ts">
import {ref, watch} from "vue";
import { useStore } from "@/store";

const store = useStore()
const dialog_open = ref(false)
const new_secret = ref(null)

const saveSecret = () => {
  // Handle saving the secret here
  console.log('new secret', new_secret.value);
  store.setApiKey(new_secret.value);
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
      <span class="text-h5">Set Secret</span>
    </v-card-title>
    <v-card-item>
      <v-text-field
          label="Enter a secret phrase"
          v-model="new_secret"
          :placeholder="store.user_secret"
          :persistent-placeholder=true
          :hint="'Api key: ' + store.user_api_key"
      ></v-text-field>
      <v-card-text v-if="store?.user_api_key" class="text-caption py-0 my-0"> </v-card-text>
    </v-card-item>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn color="primary" @click="dialog_open = false">
        Cancel
      </v-btn>

      <v-btn v-bind="props" color="primary" @click="dialog_open = false">
        Get key
        <v-tooltip
            activator="parent"
            location="top"
        >I have a secret</v-tooltip>
      </v-btn>
      <v-btn v-bind="props" color="primary" @click="saveSecret(); dialog_open = false" id="saveSecret">
        Change secret
        <v-tooltip
            activator="parent"
            location="top"
        >I want to change my secret</v-tooltip>
      </v-btn>
    </v-card-actions>
  </v-card>
  </v-dialog>
</template>