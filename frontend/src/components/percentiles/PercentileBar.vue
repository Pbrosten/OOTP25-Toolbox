
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
    // Pre-formatted raw stat value shown to the right of the bar
    // (Savant-style), e.g. "3.13", ".223", "55". Optional -- omitted
    // entirely if the caller has no raw value to show for this stat.
    value: {
      type: String,
      default: null,
    },
    // Ticket 0086: this stat's percentile if the player reached their
    // talent-grade (potential/ceiling) ratings instead of their current
    // ones. Optional -- most callers won't have one (e.g. a stat with no
    // talent-grade counterpart at all, like basepath ratings or the
    // catcher_arm/infield_arm/etc. fielding "tool" grades). Only renders
    // a shadow when it's a real number strictly greater than `percentile`
    // -- a prospect already performing at or above their own ceiling
    // (current == potential, the common case once a player's fully
    // physically matured) shows no shadow at all.
    potentialPercentile: {
      type: Number,
      default: null,
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
    showPotentialShadow() {
      return (
        typeof this.potentialPercentile === 'number' &&
        this.potentialPercentile > this.percentile
      )
    },
  },
}
</script>

<template>
  <div class="grid grid-cols-[150px_1fr_44px] items-center gap-3 my-3 w-full">
    <!-- Right-aligned label, short dotted underline beneath it (Savant-style leader) -->
    <div class="whitespace-nowrap font-bold text-sm text-right">
      <span class="inline-block border-b-2 border-dotted border-team pb-0.5">{{ label }}</span>
    </div>

    <!-- Bar container -->
    <div class="relative bg-gray-300 h-5 rounded-md w-full">
      <!-- Potential (ticket 0086): extends past the current fill out to
           this player's talent-grade ceiling for this stat, when it's
           higher than where they currently rank. Painted first (and
           given its own stacking context via `relative` on the current
           fill below) so the current fill always renders on top of it. -->
      <div
        v-if="showPotentialShadow"
        class="absolute inset-y-0 left-0 h-full rounded-md bg-gray-500/40"
        :style="{
          width: potentialPercentile + '%',
          boxShadow: 'inset 0 0 6px rgba(0,0,0,0.35)',
        }"
        :title="`Potential: ${potentialPercentile}th percentile`"
      ></div>

      <!-- Colored filled bar -->
      <div
        class="relative h-full transition-all duration-500 rounded-l-md"
        :style="{
          width: percentile + '%',
          backgroundColor: computedColor
        }"
      ></div>

      <!-- Head circle -->
      <div
        class="absolute top-1/2 -translate-y-1/2 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center text-white border-2 border-white transition-all duration-500"
        :style="{
          left: `calc(${percentile}% - 12px)`,
          backgroundColor: computedColor
        }"
      >
        {{ percentile }}
      </div>
    </div>

    <!-- Raw stat value -->
    <div class="whitespace-nowrap text-sm text-gray-600 text-left">
      {{ value ?? '' }}
    </div>
  </div>
</template>