export type UsePaginationParams<T> = {
  data?: T[];
  currentPage?: number;
  pageSize?: number;
};

export function usePagination<T>(params: UsePaginationParams<T>) {
  const currentPage = ref(params.currentPage ?? 1);
  const pageSize = ref(params.pageSize ?? 10);
  const data = ref(params.data ?? []);

  const returnLowestLimit = computed(() => {
    return currentPage.value * pageSize.value - pageSize.value;
  });

  const returnHighestLimit = computed(() => currentPage.value * pageSize.value);

  const calculatedRows = computed(() => {
    if (data) {
      return data.value.slice(returnLowestLimit.value, returnHighestLimit.value);
    } else {
      return [];
    }
  });

  const totalPages = computed(() => {
    return data.value.length > pageSize.value ? Math.ceil(data.value.length / pageSize.value) : 1;
  });

  function setData(newData: T[]) {
    data.value = newData;
  }

  function setCurrentPage(page: number) {
    currentPage.value = page;
  }

  function setPageSize(size: number) {
    pageSize.value = size;
  }

  watchEffect(() => {
    if (currentPage.value > totalPages.value) {
      setCurrentPage(currentPage.value - 1);
    }
  });

  return {
    data: calculatedRows,
    totalPages,
    currentPage,
    pageSize,
    setData,
    setCurrentPage,
    setPageSize,
  };
}
