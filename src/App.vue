<template>
  <component :is="currentView" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import IndexView from './views/IndexView.vue';
import AiAssistantView from './views/AiAssistantView.vue';
import ConfigEditorView from './views/ConfigEditorView.vue';
import { printInfo, printSKMCJ } from './utils/logUtil';

const routes = {
  '/': IndexView,
  '/ai': AiAssistantView,
  '/config': ConfigEditorView,
};

const currentPath = ref(window.location.hash.slice(1) || '/');
const currentView = ref(routes[currentPath.value] || IndexView);

const handleHashChange = () => {
  currentPath.value = window.location.hash.slice(1) || '/';
  currentView.value = routes[currentPath.value] || IndexView;
};

onMounted(() => {
  window.addEventListener('hashchange', handleHashChange);
});

onUnmounted(() => {
  window.removeEventListener('hashchange', handleHashChange);
});

setTimeout(() => {
  console?.clear();
  printSKMCJ();
  printInfo();
}, 1500);
</script>

<style lang="scss">
::selection {
  background-color: #8b968d;
  color: #fff;
}
</style>
