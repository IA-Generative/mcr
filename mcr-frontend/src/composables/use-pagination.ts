export type UsePaginationParams = {
  currentPage?: number;
  pageSize?: number;
};

export function usePagination(params: UsePaginationParams) {
  const currentPage = ref(params.currentPage ?? 1);
  const pageSize = ref(params.pageSize ?? 10);

  function setCurrentPage(page: number) {
    currentPage.value = page;
  }

  function setPageSize(size: number) {
    pageSize.value = size;
    currentPage.value = 1;
  }

  return {
    currentPage,
    pageSize,
    setCurrentPage,
    setPageSize,
  };
}
