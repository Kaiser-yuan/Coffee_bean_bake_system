<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': app.sidebarCollapsed }">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <router-link to="/dashboard" class="logo">
          <span class="logo-icon">☕</span>
          <span class="logo-text">CoffeeRoast</span>
        </router-link>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in mainNavItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="nav-item--active"
          :title="item.label"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 系统设置固定在底部 -->
      <div class="sidebar-bottom">
        <router-link
          to="/settings"
          class="nav-item"
          active-class="nav-item--active"
          title="系统设置"
        >
          <span class="nav-icon">⚙</span>
          <span class="nav-label">系统设置</span>
        </router-link>
      </div>

      <div class="sidebar-footer">
        <span class="text-xs text-tertiary">v0.2.0 · Mock</span>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <button class="toggle-btn" @click="app.toggleSidebar" title="折叠侧栏">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="15" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <span class="page-title">{{ $route.meta.title || '' }}</span>
        </div>
        <div class="topbar-right">
          <span class="text-sm text-secondary">烘焙师</span>
        </div>
      </header>
      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '../../stores/app'

const app = useAppStore()

const mainNavItems = [
  { path: '/dashboard', label: '系统总览', icon: '▦' },
  { path: '/green-beans', label: '生豆管理', icon: '◫' },
  { path: '/roasting', label: '烘焙分析', icon: '◴' },
  { path: '/evaluations', label: '评价管理', icon: '☰' },
]
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--app-bg);
}

/* ---------- 侧栏 ---------- */
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--surface);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal), min-width var(--transition-normal);
  z-index: 10;
}

.sidebar-collapsed .sidebar {
  width: var(--sidebar-collapsed-width);
  min-width: var(--sidebar-collapsed-width);
}

.sidebar-header {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  padding: 0 var(--sp-4);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-weight: 600;
  font-size: var(--fs-md);
  color: var(--text-primary);
  text-decoration: none;
}

.logo-icon {
  font-size: 20px;
}

.sidebar-collapsed .logo-text {
  display: none;
}

/* 主导航区域 */
.sidebar-nav {
  flex: 1;
  padding: var(--sp-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

/* 底部设置 */
.sidebar-bottom {
  padding: var(--sp-2);
  border-top: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--radius-md);
  font-size: var(--fs-base);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
  white-space: nowrap;
  height: 36px;
}

.nav-item:hover {
  background: #f5f7fb;
  color: var(--text-primary);
}

.nav-item--active {
  background: var(--primary-subtle);
  color: var(--primary);
  font-weight: 500;
}

.nav-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-collapsed .nav-label {
  display: none;
}

.sidebar-footer {
  padding: var(--sp-3) var(--sp-4);
  border-top: 1px solid var(--border-default);
  flex-shrink: 0;
}

/* ---------- 主区域 ---------- */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--app-bg);
}

.topbar {
  height: var(--topbar-height);
  background: var(--surface);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--sp-6);
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--sp-1);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-btn:hover {
  background: var(--app-bg);
  color: var(--text-primary);
}

.page-title {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: var(--sp-6);
  min-width: 0;
}
</style>
