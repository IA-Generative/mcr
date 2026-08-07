<template>
  <div class="separator flex items-center pt-2 pb-8 text-center font-medium text-black">
    <span>{{ $t('common.or') }}</span>
  </div>
</template>

<style scoped>
.separator::before,
.separator::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #ddd;
}

.separator::before {
  margin-right: 10px;
}

.separator::after {
  margin-left: 10px;
}
</style>
