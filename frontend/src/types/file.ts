export interface FileReference {
  id: string;
  original_filename: string;
  uploaded_at: string;
  is_duplicate: boolean;
  file_url: string;
  file_hash: string;
  file_type: string;
  size: number;
  reference_count: number;
}

export interface FileUploadResponse {
  file_reference: FileReference;
  is_duplicate: boolean;
  storage_saved: number;
  message: string;
}

export interface StorageStats {
  total_files_uploaded: number;
  unique_files_stored: number;
  total_size_uploaded: number;
  actual_size_stored: number;
  storage_saved: number;
  total_size_uploaded_mb: number;
  actual_size_stored_mb: number;
  storage_saved_mb: number;
  savings_percentage: number;
  deduplication_ratio: number;
  last_updated: string;
}

export interface SearchParams {
  search?: string;
  file_type?: string[];
  min_size?: number;
  max_size?: number;
  from_date?: string;
  to_date?: string;
  duplicates_only?: boolean;
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DetailedStats {
  basic_stats: StorageStats;
  file_type_breakdown: Array<{
    file_type: string;
    count: number;
    total_size: number;
    total_references: number;
  }>;
  most_duplicated_files: FileReference[];
  recent_uploads: FileReference[];
  recent_duplicates: FileReference[];
}

// Legacy interface for backward compatibility
export interface File extends FileReference {} 