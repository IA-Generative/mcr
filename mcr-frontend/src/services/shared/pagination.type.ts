export type PaginationQuery = {
  page: number;
  search?: string;
  page_size: number;
};

export type PaginatedResponse<T> = {
  total_items: number;
  total_pages: number;
  page: number;
  data: T[];
};
