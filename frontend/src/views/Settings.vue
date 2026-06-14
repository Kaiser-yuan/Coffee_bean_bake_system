<template>
  <div class="settings-page">
    <div class="page-header">
      <h2 class="page-heading">系统设置</h2>
    </div>

    <!-- 标签页切换 -->
    <div class="tabs-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 标准词表 -->
    <template v-if="activeTab === 'terms'">
      <section class="settings-section">
        <h3 class="section-title">标准词表管理</h3>
        <p class="text-sm text-tertiary mb-md">
          已使用的词条只能停用，不能删除。停用后不再出现在录入选项中，但仍会在历史记录中正确显示。
        </p>

        <div class="term-categories">
          <div v-for="cat in termCategories" :key="cat.key" class="term-cat">
            <h4 class="cat-title">{{ cat.label }}</h4>
            <div class="term-table">
              <div
                v-for="term in getTermsByCategory(cat.key)"
                :key="term.id"
                class="term-row"
                :class="{ inactive: !term.active }"
              >
                <span class="term-value">{{ term.value }}</span>
                <span class="term-usage text-xs text-tertiary">已使用 {{ term.usageCount }} 次</span>
                <label class="toggle" @click.stop>
                  <input
                    type="checkbox"
                    :checked="term.active"
                    :disabled="term.usageCount > 0 && term.active"
                    @change="toggleTerm(term)"
                    :title="term.usageCount > 0 && term.active ? '已有使用记录，只能停用' : ''"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- 烘焙机与 CSV 配置 -->
    <template v-if="activeTab === 'machine'">
      <section class="settings-section">
        <h3 class="section-title">烘焙机配置</h3>
        <p class="text-sm text-tertiary mb-md">狙击手 M1 烘焙机</p>
        <div class="machine-info">
          <div class="machine-item">
            <span class="machine-label">品牌 / 型号</span>
            <span class="machine-value">狙击手 M1</span>
          </div>
          <div class="machine-item">
            <span class="machine-label">电流</span>
            <span class="machine-value">单相 220V</span>
          </div>
          <div class="machine-item">
            <span class="machine-label">最大烘焙量</span>
            <span class="machine-value">1.2kg</span>
          </div>
        </div>
      </section>
      <section class="settings-section">
        <h3 class="section-title">Kaleido M1 CSV 解析规则</h3>
        <div class="csv-spec">
          <div class="csv-spec-item">
            <span class="csv-spec-label">支持文件名</span>
            <span class="csv-spec-value">日期_顺序号.csv（例：260530_9.csv）</span>
          </div>
          <div class="csv-spec-item">
            <span class="csv-spec-label">解析字段</span>
            <span class="csv-spec-value">index, time, BT, ET, RoR, SV, HP, HPM, SM, RL, PS</span>
          </div>
          <div class="csv-spec-item">
            <span class="csv-spec-label">阶段标注</span>
            <span class="csv-spec-value">入豆 - 转黄 - 一爆开始 - 一爆结束 - 出豆</span>
          </div>
          <div class="csv-spec-item">
            <span class="csv-spec-label">参考</span>
            <span class="csv-spec-value">基于 260530_9.csv 与 260530_10.csv 解析</span>
          </div>
        </div>
      </section>
    </template>

    <!-- 用户管理 -->
    <template v-if="activeTab === 'users'">
      <section class="settings-section">
        <h3 class="section-title">用户管理</h3>
        <EmptyState icon="👤" title="用户管理占位" description="第一版为单用户模式，多用户功能待后续版本" />
      </section>
    </template>

    <!-- 文件与备份 -->
    <template v-if="activeTab === 'files'">
      <section class="settings-section">
        <h3 class="section-title">文件与备份</h3>
        <EmptyState icon="🔧" title="未配置" description="真实接口完成前，备份功能暂不可用" />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { mockTerms } from '../mock'
import type { StandardTerm } from '../types'
import EmptyState from '../components/common/EmptyState.vue'

const activeTab = ref('terms')

const tabs = [
  { key: 'terms', label: '标准词表' },
  { key: 'machine', label: '烘焙机与CSV' },
  { key: 'users', label: '用户管理' },
  { key: 'files', label: '文件与备份' },
]

const termCategories = [
  { key: 'flavor', label: '风味标签' },
  { key: 'defect', label: '缺陷标签' },
  { key: 'roast_level', label: '烘焙度' },
  { key: 'process', label: '处理法' },
  { key: 'brew_method', label: '冲煮方式' },
  { key: 'evaluator_type', label: '评价者类型' },
  { key: 'drink_temperature', label: '饮用温度' },
  { key: 'drink_form', label: '饮用形式' },
]

function getTermsByCategory(cat: string) {
  return mockTerms.filter(t => t.category === cat)
}

function toggleTerm(term: StandardTerm) {
  if (term.usageCount > 0 && term.active) return
  term.active = !term.active
}
</script>

<style scoped>
.settings-page { max-width: 900px; }

.page-header { margin-bottom: var(--sp-4); }
.page-heading { font-size: var(--fs-xl); font-weight: 600; }

/* Tabs */
.tabs-bar {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--border-default);
  margin-bottom: var(--sp-6);
}

.tab-btn {
  padding: var(--sp-2) var(--sp-5);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  font-size: var(--fs-base);
  font-family: var(--font-sans);
  color: var(--text-secondary);
  cursor: pointer;
  font-weight: 500;
}

.tab-btn:hover { color: var(--text-primary); }

.tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

/* Sections */
.settings-section {
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--sp-6);
  margin-bottom: var(--sp-4);
}

.section-title {
  font-size: var(--fs-md);
  font-weight: 600;
  margin-bottom: var(--sp-3);
}

.mb-md { margin-bottom: var(--sp-3); }

/* Term categories */
.term-categories {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.cat-title {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--sp-2);
}

.term-table {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.term-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-1) var(--sp-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
}

.term-row.inactive {
  opacity: 0.4;
}

.term-row.inactive .term-value {
  text-decoration: line-through;
}

.term-value { font-weight: 500; }

/* Toggle switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 32px;
  height: 18px;
  cursor: pointer;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--border-default);
  border-radius: 9px;
  transition: 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 14px;
  height: 14px;
  left: 2px;
  bottom: 2px;
  background: #fff;
  border-radius: 50%;
  transition: 0.2s;
}

.toggle input:checked + .toggle-slider {
  background: var(--primary);
}

.toggle input:checked + .toggle-slider::before {
  transform: translateX(14px);
}

.toggle input:disabled + .toggle-slider {
  opacity: 0.5;
  cursor: not-allowed;
}

.toggle input:disabled + .toggle-slider::before {
  opacity: 0.6;
}

/* Backup */
.backup-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.backup-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-2) 0;
  border-bottom: 1px solid var(--border-default);
}

.backup-item:last-child { border-bottom: none; }

.machine-info {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.machine-item {
  display: flex;
  gap: var(--sp-3);
  font-size: var(--fs-sm);
}

.machine-label { color: var(--text-tertiary); min-width: 120px; }
.machine-value { font-weight: 500; }

.csv-spec {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.csv-spec-item {
  display: flex;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
}

.csv-spec-label { color: var(--text-tertiary); min-width: 100px; flex-shrink: 0; }
.csv-spec-value { font-family: var(--font-mono); font-size: var(--fs-xs); }

.backup-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
