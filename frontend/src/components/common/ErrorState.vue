<template>
  <div class="error-state">
    <span class="error-icon">⚠️</span>
    <p class="error-title">{{ title }}</p>
    <p v-if="message" class="error-message">{{ message }}</p>
    <button v-if="retry" class="retry-btn" @click="$emit('retry')">重试</button>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  message?: string
  retry?: boolean
}>(), {
  title: '加载失败',
  retry: false,
})

defineEmits<{ retry: [] }>()
</script>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--sp-8);
  gap: var(--sp-2);
}

.error-icon {
  font-size: 28px;
  opacity: 0.5;
}

.error-title {
  font-size: var(--fs-base);
  color: var(--danger);
  font-weight: 500;
}

.error-message {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
}

.retry-btn {
  margin-top: var(--sp-3);
  padding: var(--sp-1) var(--sp-4);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text-primary);
  cursor: pointer;
  font-size: var(--fs-sm);
  height: 32px;
}

.retry-btn:hover {
  background: var(--app-bg);
  border-color: var(--border-strong);
}
</style>
