<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { useGlobal } from '@/composables/globals'
import type { MediaStoryFragment } from '@/types'
import type { PreferenceValues } from '@/worldPreferences'
import { mediaContentUrl } from './fragmentUtils'
import { mediaRole } from './fragmentViewUtils'
import { castStage, figureStyle, type StageExtent } from './stage'
import { selectedClip } from './stageBindings'

/**
 * A fixed logical canvas of `extent` pixels, scaled as a whole to the column
 * and keeping its aspect ratio. Everything inside is laid out in logical
 * pixels, so a figure drawn at its natural size is that size times the scale.
 * The viewer's preferences hide bound media and choose each figure's clip;
 * changing them redraws here and never takes a story step.
 */
const props = defineProps<{
  images: MediaStoryFragment[]
  extent: StageExtent
  preferences: PreferenceValues
}>()

const { remapURL } = useGlobal()
const frame = ref<HTMLElement | null>(null)
// The frame's width is observed; the scale follows it and the extent, which
// can arrive after the frame has settled and so fire no resize of its own.
const frameWidth = ref(0)
const scale = computed(() => (frameWidth.value || props.extent.width) / props.extent.width)
let observer: ResizeObserver | undefined

onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    frameWidth.value = entry!.contentRect.width
  })
  observer.observe(frame.value!)
})
onBeforeUnmount(() => observer?.disconnect())

const cast = computed(() => castStage(props.images, props.preferences))
// A figure is keyed by its resource, so one restated in a later step stays the
// same element (and will not replay an entrance). RITs are content-addressed,
// so repeats of one resource are numbered; media with no RIT keys on its uid.
// The clip is resolved and recorded on the element; the still is what draws.
const placed = computed(() => {
  const repeats = new Map<string, number>()
  return cast.value.figures.map(({ figure, index }) => {
    const rit = figure.rit_id
    const repeat = rit ? (repeats.get(rit) ?? 0) : 0
    if (rit) repeats.set(rit, repeat + 1)
    return {
      figure,
      key: rit ? `${rit}#${repeat}` : figure.uid,
      style: figureStyle(figure, index, props.extent),
      clip: selectedClip(figure, props.preferences),
    }
  })
})
const source = (fragment: MediaStoryFragment): string => remapURL(mediaContentUrl(fragment)!)
</script>

<template>
  <div
    ref="frame"
    class="stage-frame mb-4"
    data-testid="stage"
    :style="{
      aspectRatio: `${extent.width} / ${extent.height}`,
      maxWidth: `calc(55vh * ${extent.width / extent.height})`,
    }"
  >
    <div
      class="stage-canvas"
      :style="{
        width: `${extent.width}px`,
        height: `${extent.height}px`,
        transform: `scale(${scale})`,
      }"
    >
      <img
        v-if="cast.backdrop"
        :src="source(cast.backdrop)"
        :alt="cast.backdrop.text ?? ''"
        class="stage-backdrop"
        data-stage-role="narrative_im"
      >
      <img
        v-for="{ figure, key, style, clip } in placed"
        :key="key"
        :src="source(figure)"
        :alt="figure.text ?? ''"
        :style="style"
        :data-stage-role="mediaRole(figure)"
        :data-clip="clip"
        class="stage-figure"
      >
    </div>
  </div>
</template>

<style scoped>
.stage-frame {
  background: #000;
  margin-left: auto;
  margin-right: auto;
  overflow: hidden;
  position: relative;
  /* Scrolled to on each update; clear the fixed app bar rather than sit under it. */
  scroll-margin-top: calc(var(--v-layout-top, 0px) + 16px);
  width: 100%;
}

.stage-canvas {
  left: 0;
  position: absolute;
  top: 0;
  transform-origin: top left;
}

.stage-canvas img {
  image-rendering: pixelated;
  position: absolute;
}

.stage-backdrop {
  height: 100%;
  left: 0;
  top: 0;
  width: 100%;
}

.stage-figure {
  max-width: none;
}
</style>
