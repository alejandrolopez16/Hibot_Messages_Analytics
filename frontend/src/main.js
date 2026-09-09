import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import router from './router/index.js'
import App from './App.vue'
import './index.css'

createApp(App).use(router).mount('#app')
