<template>
  <div class="skeleton-loader">
    <div
      class="skeleton"
      :style="{
        width: width + 'px',
        height: height + 'px',
        borderRadius: borderRadius + 'px',
      }"
    ></div>
  </div>
</template>

<script lang="ts" setup>
defineProps({
  width: {
    type: Number,
    default: 100,
  },
  height: {
    type: Number,
    default: 20,
  },
  borderRadius: {
    type: Number,
    default: 4,
  },
});
</script>

<style scoped>
.skeleton-loader {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton {
  background-color: var(--grey-900-175);
  position: relative;
  overflow: hidden;
}

.skeleton::before {
  content: '';
  display: block;
  position: absolute;
  top: 0;
  left: -100%;
  height: 100%;
  width: 100%;
  background: linear-gradient(
    to right,
    transparent 0%,
    var(--grey-1000-100-active) 50%,
    transparent 100%
  );
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% {
    left: -100%;
  }
  100% {
    left: 100%;
  }
}
</style>
