<script setup>
import { state } from './store/app'
import Toast from './components/Toast.vue'
import Overlay from './components/Overlay.vue'
import HomePage from './pages/HomePage.vue'
import TemplatesPage from './pages/TemplatesPage.vue'
import MaterialPage from './pages/MaterialPage.vue'
import GeneratingPage from './pages/GeneratingPage.vue'
import ResultPage from './pages/ResultPage.vue'
import AvatarsPage from './pages/AvatarsPage.vue'
import WorksPage from './pages/WorksPage.vue'
import MePage from './pages/MePage.vue'
import BalancePage from './pages/BalancePage.vue'
import SupportPage from './pages/SupportPage.vue'
import SettingsPage from './pages/SettingsPage.vue'
import ChangePasswordPage from './pages/ChangePasswordPage.vue'

const pages = {
  home: HomePage,
  templates: TemplatesPage,
  material: MaterialPage,
  generating: GeneratingPage,
  result: ResultPage,
  avatars: AvatarsPage,
  works: WorksPage,
  me: MePage,
  balance: BalancePage,
  support: SupportPage,
  settings: SettingsPage,
  'change-password': ChangePasswordPage
}
</script>

<template>
  <div class="screen">
    <component :is="pages[state.cur]" :key="state.cur" class="page" :class="state.dir" />
    <Overlay />
    <Toast />
  </div>
</template>
