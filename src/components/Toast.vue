<script setup>
import { state } from '../store/app'
</script>

<template>
  <div class="toast" :class="{ on: state.toastMsg }">{{ state.toastMsg }}</div>
</template>
