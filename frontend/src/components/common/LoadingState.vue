<template>
  <div class="loading-state">
    <div class="skeleton">
      <div class="skeleton-line skeleton-line--title"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line skeleton-line--short"></div>
    </div>
    <span v-if="text" class="loading-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ text?: string }>()
</script>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--sp-8);
  gap: var(--sp-4);
  color: var(--text-secondary);
}

.skeleton {
  width: 100%;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.skeleton-line {
  height: 14px;
  background: linear-gradient(90deg, var(--border-default) 25%, var(--surface-subtle) 50%, var(--border-default) 75%);
  background-size: 200% 100%;
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-line--title {
  height: 18px;
  width: 50%;
}

.skeleton-line--short {
  width: 70%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.loading-text {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
}
</style>
