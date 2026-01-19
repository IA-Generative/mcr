import type { MutationOptions } from '@tanstack/vue-query';

export type Nullable<T> = T | null;

type InferMutationTypes<TFn extends (...args: any) => any> = {
  TData: Awaited<ReturnType<TFn>>;
  TVariables: Parameters<TFn>[0];
};

export type ExtraMutationOptions<TFn extends (...args: any) => any> = Omit<
  MutationOptions<
    InferMutationTypes<TFn>['TData'],
    Error,
    InferMutationTypes<TFn>['TVariables'],
    unknown
  >,
  'mutationFn'
>;
