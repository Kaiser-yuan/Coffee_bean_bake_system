<template>
  <div class="login-page">
    <section class="login-card">
      <div class="login-heading">
        <div class="brand-mark">CoffeeRoast</div>
        <h1>登录后台</h1>
        <p>使用本地后端管理员账号进入联调环境。</p>
      </div>

      <form class="login-form" @submit.prevent="submit">
        <label class="field">
          <span>用户名</span>
          <input v-model.trim="username" class="input" autocomplete="username" />
        </label>

        <label class="field">
          <span>密码</span>
          <input
            v-model="password"
            class="input"
            type="password"
            autocomplete="current-password"
          />
        </label>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <button class="login-btn" type="submit" :disabled="auth.loading || !canSubmit">
          {{ auth.loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="login-hint">
        首次使用请在本地后端完成首个管理员账号初始化后再登录。
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const errorMessage = ref('')

const canSubmit = computed(() => username.value.length > 0 && password.value.length > 0)

async function submit() {
  errorMessage.value = ''
  try {
    await auth.login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string'
      ? route.query.redirect
      : '/dashboard'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = error instanceof ApiError
      ? error.message
      : '登录失败，请稍后重试'
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at top left, rgba(47, 107, 255, 0.12), transparent 32%),
    var(--app-bg);
  padding: var(--sp-6);
}

.login-card {
  width: min(420px, 100%);
  background: var(--surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-overlay);
  padding: var(--sp-8);
}

.login-heading {
  margin-bottom: var(--sp-6);
}

.brand-mark {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--primary-subtle);
  color: var(--primary);
  font-weight: 600;
  margin-bottom: var(--sp-4);
}

.login-heading h1 {
  font-size: var(--fs-2xl);
  margin-bottom: var(--sp-2);
}

.login-heading p,
.login-hint {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  font-size: var(--fs-sm);
  font-weight: 500;
}

.input {
  height: var(--input-height);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 0 var(--sp-3);
  font: inherit;
}

.input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-subtle);
}

.error-message {
  color: var(--danger);
  background: var(--danger-subtle);
  border: 1px solid rgba(217, 75, 75, 0.3);
  border-radius: var(--radius-md);
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--fs-sm);
}

.login-btn {
  height: 38px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: white;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-hint {
  margin-top: var(--sp-5);
}
</style>
