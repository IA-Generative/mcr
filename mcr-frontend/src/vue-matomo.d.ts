// vue-matomo ships no type declarations; declare the default export as a Vue plugin.
declare module 'vue-matomo' {
  import type { Plugin } from 'vue';
  const VueMatomo: Plugin;
  export default VueMatomo;
}
