export type PaginationQuery = {
  page: number;
  search?: string;
  page_size: number;
};

export type PaginatedResponse<T> = {
  totalItems: number;
  totalPages: number;
  page: number;
  data: T[];
};
