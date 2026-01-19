<script lang="ts" setup>
import { DsfrTableHeaders } from '@gouvminint/vue-dsfr';
import { DsfrTableRow } from '@gouvminint/vue-dsfr';
import type { DsfrTableProps, DsfrTableRowProps } from '@gouvminint/vue-dsfr';

export type { DsfrTableProps };

withDefaults(defineProps<Omit<DsfrTableProps, 'currentPage' | 'resultsDisplayed'>>(), {
  headers: () => [],
  rows: () => [],
  rowKey: undefined,
});

const getRowData = (row: DsfrTableProps['rows']) => {
  return Array.isArray(row) ? row : (row as unknown as DsfrTableRowProps).rowData;
};
</script>

<template>
  <div
    class="fr-table m-0 p-0"
    :class="{ 'fr-table--no-caption': noCaption }"
  >
    <table>
      <caption class="caption">
        {{
          title
        }}
      </caption>
      <thead>
        <slot name="header">
          <DsfrTableHeaders
            v-if="headers && headers.length"
            :headers="headers"
          />
        </slot>
      </thead>
      <tbody>
        <slot />
        <template v-if="rows && rows.length">
          <DsfrTableRow
            v-for="(row, i) of rows"
            :key="
              rowKey && getRowData(row as string[][])
                ? typeof rowKey === 'string'
                  ? getRowData(row as string[][])![headers.indexOf(rowKey)].toString()
                  : rowKey(getRowData(row as string[][]))
                : i
            "
            :row-data="getRowData(row as string[][])"
            :row-attrs="'rowAttrs' in row ? row.rowAttrs : {}"
          />
        </template>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.flex {
  display: flex;
}

.justify-right {
  justify-content: right;
}

.ml-1 {
  margin-left: 1rem;
}

.self-center {
  align-self: center;
}
</style>
