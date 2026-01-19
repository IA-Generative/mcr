import type { QUERY_KEYS } from '@/plugins/vue-query';
import type { PaginationQuery } from '@/services/shared/pagination.type';
import { useQueryClient, useQuery, useMutation } from '@tanstack/vue-query';

export type UseTableActionsParams<T, U> = {
  queryKey: QUERY_KEYS;
  getDataFn: (pagination: PaginationQuery) => Promise<T>;
  removeDataFn: (id: number) => Promise<U>;
};

export function useTableActions<T, U>({
  getDataFn,
  queryKey,
  removeDataFn,
}: UseTableActionsParams<T, U>) {
  const queryClient = useQueryClient();
  const search = ref<string>();

  const getDataQuery = useQuery({
    queryKey: [queryKey, { search: search.value }],
    queryFn: () =>
      getDataFn({
        search: search.value,
      }),
  });

  const deleteRowMutation = useMutation({
    mutationFn: removeDataFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [queryKey] });
    },
  });

  function onSearch() {
    queryClient.invalidateQueries({ queryKey: [queryKey] });
  }

  return {
    search,
    getDataQuery,
    deleteRowMutation,
    onSearch,
  };
}
