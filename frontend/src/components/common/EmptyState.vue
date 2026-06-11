<template>
  <div class="empty-state">
    <span class="empty-icon">{{ icon }}</span>
    <p class="empty-title">{{ title }}</p>
    <p v-if="description" class="empty-desc">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  icon?: string
  title?: string
  description?: string
}>(), {
  icon: '📭',
  title: '暂无数据',
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--sp-8);
  gap: var(--sp-2);
}

.empty-icon {
  font-size: 28px;
  opacity: 0.35;
}

.empty-title {
  font-size: var(--fs-base);
  color: var(--text-secondary);
  font-weight: 500;
}

.empty-desc {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
}
</style>
