<template>
  <div class="pagination-container">
    <div class="flex justify-right">
      <div class="self-center">
        <span>Résultats par page : </span>
        <select
          v-model="optionSelected"
          @change="onSelectPageSize"
        >
          <option
            v-for="(option, idx) in pageSizeOptions"
            :key="idx"
            :value="option"
          >
            {{ option }}
          </option>
        </select>
      </div>
      <div class="flex ml-1">
        <span class="self-center">Page {{ currentPage }} sur {{ totalPages }}</span>
      </div>
      <div class="flex ml-1">
        <button
          class="fr-icon-arrow-left-s-first-line"
          @click="goFirstPage()"
        />
        <button
          class="fr-icon-arrow-left-s-line"
          @click="goPreviousPage()"
        />
        <button
          class="fr-icon-arrow-right-s-line"
          @click="goNextPage()"
        />
        <button
          class="fr-icon-arrow-right-s-last-line"
          @click="goLastPage()"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    currentPage?: number;
    pageSize?: number;
    totalPages: number;
    pageSizeOptions?: number[];
  }>(),
  {
    currentPage: 1,
    pageSize: 10,
    pageSizeOptions: () => [5, 10, 25, 50, 100],
  },
);
const emit = defineEmits<{
  onPageChange: [page: number];
  onPageSizeChange: [size: number];
}>();

const optionSelected = ref(props.pageSize);

function onSelectPageSize(e: Event) {
  emit('onPageSizeChange', Number((e.target as HTMLInputElement).value));
}

const goFirstPage = () => {
  emit('onPageChange', 1);
};

const goPreviousPage = () => {
  let page = props.currentPage - 1;
  if (page <= 0) {
    page = 1;
  }
  emit('onPageChange', page);
};

const goNextPage = () => {
  let page = props.currentPage + 1;
  if (page > props.totalPages) {
    page = props.totalPages;
  }
  emit('onPageChange', page);
};
const goLastPage = () => {
  emit('onPageChange', props.totalPages);
};
</script>

<style scoped></style>
