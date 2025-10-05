
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
  <div class="percentile-bar">
    <div class="label">{{ label }}</div>
    <div class="bar-container">
      <div
        class="bar"
        :style="{
          width: percentile + '%',
          backgroundColor: computedColor
        }"
      ></div>
      <div class="percentile-text">{{ percentile }}%</div>
    </div>
  </div>
</template>

<style scoped>
.percentile-bar {
  display: grid;
  grid-template-columns: 150px 1fr;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
  width: 100%;
}

.label {
  white-space: nowrap;
  font-weight: bold;
  font-size: 14px;
}

.bar-container {
  position: relative;
  background: #e0e0e0;
  height: 20px;
  border-radius: 6px;
  overflow: hidden;
  width: 100%;
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
