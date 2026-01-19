export type PaginationQuery = {
  // page: number;
  search?: string;
  // pageSize: number;
};

export type PaginatedResponse<T> = {
  totalItems: number;
  totalPages: number;
  page: number;
  data: T[];
};
