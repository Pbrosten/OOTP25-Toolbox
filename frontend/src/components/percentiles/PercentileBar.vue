
<script>
export default {
  name: "PercentileBar",
  props: {
    label: {
      type: String,
      required: true,
    },
    percentile: {
      type: Number,
      required: true,
      validator(val) {
        return val >= 0 && val <= 100
      },
    },
  },
  computed: {
    computedColor() {
      // Normalize to [0,1]
      const p = this.percentile / 100

      // Color anchors (rgb arrays)
      const high = [216, 33, 41]     // red-ish
      const mid = [180, 207, 209]    // neutral / light blue–gray
      const low = [54, 97, 173]      // deep blue

      let r, g, b

      if (p >= 0.5) {
        // Interpolate from mid → high
        const t = (p - 0.5) * 2  // maps 0.5→0 to 1.0→1
        r = Math.round(mid[0] + t * (high[0] - mid[0]))
        g = Math.round(mid[1] + t * (high[1] - mid[1]))
        b = Math.round(mid[2] + t * (high[2] - mid[2]))
      } else {
        // Interpolate from low → mid
        const t = p * 2  // maps 0→0 to 0.5→1
        r = Math.round(low[0] + t * (mid[0] - low[0]))
        g = Math.round(low[1] + t * (mid[1] - low[1]))
        b = Math.round(low[2] + t * (mid[2] - low[2]))
      }

      return `rgb(${r}, ${g}, ${b})`
    },
  },
}
</script>

<template>
  <div class="grid grid-cols-[150px_1fr] items-center gap-3 my-3 w-full">
    <div class="whitespace-nowrap font-bold text-sm">
      {{ label }}
    </div>
    <div class="relative bg-gray-300 h-5 rounded-md overflow-hidden w-full">
      <div
        class="h-full transition-all duration-500 rounded-l-md"
        :style="{
          width: percentile + '%',
          backgroundColor: computedColor
        }"
      ></div>
      <div class="absolute right-2 top-1 font-bold text-xs text-gray-900">
        {{ percentile }}%
      </div>
    </div>
  </div>
</template>
