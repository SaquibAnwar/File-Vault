import axios from 'axios';
import { 
  FileReference, 
  FileUploadResponse, 
  StorageStats, 
  SearchParams, 
  PaginatedResponse, 
  DetailedStats
} from '../types/file';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const fileService = {
  // File Upload with Deduplication
  async uploadFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post(`${API_URL}/files/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get Files with Search and Pagination
  async getFiles(params?: SearchParams): Promise<PaginatedResponse<FileReference>> {
    const searchParams = new URLSearchParams();
    
    if (params) {
      if (params.search) searchParams.append('search', params.search);
      if (params.file_type && params.file_type.length > 0) {
        params.file_type.forEach(type => searchParams.append('file_type', type));
      }
      if (params.min_size !== undefined) searchParams.append('min_size', params.min_size.toString());
      if (params.max_size !== undefined) searchParams.append('max_size', params.max_size.toString());
      if (params.from_date) searchParams.append('from_date', params.from_date);
      if (params.to_date) searchParams.append('to_date', params.to_date);
      if (params.duplicates_only) searchParams.append('duplicates_only', 'true');
      if (params.sort_by) searchParams.append('sort_by', params.sort_by);
      if (params.page) searchParams.append('page', params.page.toString());
      if (params.page_size) searchParams.append('page_size', params.page_size.toString());
    }

    const url = searchParams.toString() ? `${API_URL}/files/?${searchParams}` : `${API_URL}/files/`;
    const response = await axios.get(url);
    return response.data;
  },

  // Advanced Search Endpoint
  async searchFiles(params: SearchParams): Promise<PaginatedResponse<FileReference>> {
    const searchParams = new URLSearchParams();
    
    if (params.search) searchParams.append('search', params.search);
    if (params.file_type && params.file_type.length > 0) {
      params.file_type.forEach(type => searchParams.append('file_type', type));
    }
    if (params.min_size !== undefined) searchParams.append('min_size', params.min_size.toString());
    if (params.max_size !== undefined) searchParams.append('max_size', params.max_size.toString());
    if (params.from_date) searchParams.append('from_date', params.from_date);
    if (params.to_date) searchParams.append('to_date', params.to_date);
    if (params.duplicates_only) searchParams.append('duplicates_only', 'true');
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);

    const response = await axios.get(`${API_URL}/files/search/?${searchParams}`);
    return response.data;
  },

  // Delete File
  async deleteFile(id: string): Promise<{ message: string; file_deleted: boolean; storage_freed: number }> {
    const response = await axios.delete(`${API_URL}/files/${id}/`);
    return response.data;
  },

  // Bulk Delete
  async bulkDeleteFiles(referenceIds: string[]): Promise<{
    message: string;
    total_storage_freed: number;
    results: Array<{
      reference_id: string;
      original_filename: string;
      file_deleted: boolean;
      storage_freed: number;
    }>;
  }> {
    const response = await axios.post(`${API_URL}/files/bulk_delete/`, {
      reference_ids: referenceIds
    });
    return response.data;
  },

  // Storage Statistics
  async getStorageStats(): Promise<StorageStats> {
    const response = await axios.get(`${API_URL}/files/stats/`);
    return response.data;
  },

  // Detailed Statistics
  async getDetailedStats(): Promise<DetailedStats> {
    const response = await axios.get(`${API_URL}/files/detailed_stats/`);
    return response.data;
  },

  // Get Available File Types
  async getFileTypes(): Promise<string[]> {
    const response = await axios.get(`${API_URL}/files/file_types/`);
    return response.data;
  },

  // Get Duplicate Files
  async getDuplicateFiles(): Promise<PaginatedResponse<FileReference>> {
    const response = await axios.get(`${API_URL}/files/duplicates/`);
    return response.data;
  },

  // Download File
  async downloadFile(fileUrl: string, filename: string): Promise<void> {
    try {
      const response = await axios.get(fileUrl, {
        responseType: 'blob',
      });
      
      // Create a blob URL and trigger download
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
      throw new Error('Failed to download file');
    }
  },

  // Utility: Format file size
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // Utility: Format date
  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}; 