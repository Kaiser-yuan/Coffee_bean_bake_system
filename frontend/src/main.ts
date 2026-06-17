import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/global.css'
import { isDemoMode } from './api/http'

// 启动时明确打印当前数据来源，便于联调时判断是否真的对接后端
// eslint-disable-next-line no-console
console.info(
  `[CoffeeRoast] 数据来源：${isDemoMode ? '演示模式 (mock)' : '真实 API'}`
)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
