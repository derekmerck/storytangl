// Note, we could also use a "v-virtual-scroll" component here.

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import StoryBlock from './StoryBlock.vue'
import { JournalEntry } from "@/types";

import { useGlobal } from "@/globals";
const { $http, $debug, $verbose, remapURL, makeMediaDict } = useGlobal()

const blocks = ref<JournalEntry>([])
const block_refs = ref([])
const block_counter = ref(0)

const handleResponse = async (response) => {
  // if response.data[0]?.label exists, set blocks.value to an empty array
  if (response.data[0]?.label) {
    blocks.value = []
  }

  // loop through the response data
  response.data.forEach(block => {
    // increment blockCounter
    block_counter.value++
    console.log(block_counter)
    // add a new field 'key' to the block
    block.key = `${block.uid}-${block_counter.value}`

    // Function to remap image URLs
    const remapMediaURL = (media) => {
      media.url = remapURL(media.url)
    }

    if (block.media) {
      Object.values(block.media).forEach(remapMediaURL),
      block.media_dict = makeMediaDict(block);
    }

    // Check and remap URLs in dialog block media
    if (block?.dialog) {
      block.dialog.forEach(dialogBlock => {
        if (dialogBlock.media) {
          Object.values(dialogBlock.media).forEach(remapMediaURL)
          dialogBlock.media_dict = makeMediaDict(dialogBlock)
        }
      })
    }
  })

  const current_block_index = blocks.value.length
  // add new blocks to existing blocks
  blocks.value.push(...response.data)

  await nextTick(() => {
    const top_block = block_refs.value[current_block_index]
    top_block.$el.scrollIntoView({behavior: current_block_index ? 'smooth' : 'auto'});
  });

}

onMounted(async () => {
  try {
    const response = await $http.value.get('/story/update')
    handleResponse(response)
  } catch (error) {
    console.error(error)
  }
})

const doAction = async (action_uid, passback) => {
  try {
    const response = await $http.value.post(
      '/story/do',
      {uid: action_uid, passback: passback }
      )
    handleResponse(response)
  } catch(error) {
    console.error(error)
  }
}

</script>

<template>

  <StoryBlock
    v-for="block in blocks"
    :key="block.key"
    ref="block_refs"
    :block="block"
    @doAction="doAction" />

  <v-card v-if="false && $debug && $verbose">
    <v-card-item>
      <v-card border>
        <v-card-text class="text-caption" >
          Blocks: {{ blocks }}
        </v-card-text>
      </v-card>
    </v-card-item>
  </v-card>

</template>
