<script setup>
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import AppTabbar from './components/AppTabbar.vue'
import AppService from './components/AppService.vue'
import LoginModal from '@/views/auth/LoginModal.vue'
</script>

<template>
  <div class="layout">
    <AppHeader />
    <main class="layout-main">
      <router-view />
    </main>
    <AppFooter />
    <AppTabbar />
    <AppService />
    <LoginModal />
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.layout-main {
  flex: 1;
}
</style>
