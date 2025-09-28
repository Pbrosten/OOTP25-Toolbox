<template>
  <div class="percentile-bar">
    <div class="label">{{ label }}</div>
    <div class="bar-container">
      <div
        class="bar"
        :style="{ width: percentile, backgroundColor: computedColor }"
      ></div>
      <div class="percentile-text">{{ percentile }}%</div>
    </div>
  </div>
</template>

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
    },
  },
  computed: {
    computedColor() {
      const percent = this.percentile / 100

      // Define colors
      const high = [216, 33, 41]     // red
      const mid = [180, 207, 209]    // light blue/gray
      const low = [54, 97, 173]      // deep blue

      let r, g, b

      if (percent >= 0.5) {
        // Interpolate from mid to high
        const t = (percent - 0.5) * 2
        r = Math.round(mid[0] + t * (high[0] - mid[0]))
        g = Math.round(mid[1] + t * (high[1] - mid[1]))
        b = Math.round(mid[2] + t * (high[2] - mid[2]))
      } else {
        // Interpolate from low to mid
        const t = percent * 2
        r = Math.round(low[0] + t * (mid[0] - low[0]))
        g = Math.round(low[1] + t * (mid[1] - low[1]))
        b = Math.round(low[2] + t * (mid[2] - low[2]))
      }

      return `rgb(${r}, ${g}, ${b})`
    },
  },
}
</script>

<style scoped>
.percentile-bar {
  margin: 12px 0;
}

.label {
  font-weight: bold;
  margin-bottom: 4px;
  font-size: 14px;
}

.bar-container {
  position: relative;
  background: #e0e0e0;
  height: 28px;
  border-radius: 6px;
  overflow: hidden;
}

.bar {
  height: 100%;
  transition: width 0.6s ease, background-color 0.6s ease;
  border-radius: 6px 0 0 6px;
}

.percentile-text {
  position: absolute;
  right: 10px;
  top: 4px;
  font-weight: bold;
  color: #222;
  font-size: 13px;
}
</style>
