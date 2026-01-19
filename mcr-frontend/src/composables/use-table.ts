import SkeletonLoader from '@/components/core/SkeletonLoader.vue';

export type TableSkeletonParams = {
  rows: number;
  cols?: number;
};

export type UseTableParams = {
  cols: number;
};

export function useTable({ cols }: UseTableParams) {
  function skeletons({ rows, cols: colsNumber }: TableSkeletonParams) {
    return new Array(rows).fill(
      new Array(colsNumber ?? cols).fill({
        component: SkeletonLoader,
      }),
    );
  }

  return {
    skeletons,
  };
}
