<template>
  <div class="separator pt-2 pb-8">
    <span>{{ $t('common.or') }}</span>
  </div>
</template>

<style scoped>
.separator {
  display: flex;
  align-items: center;
  text-align: center;
  color: #000;
  font-weight: 500;
}

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
