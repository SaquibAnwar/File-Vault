import React, { useState, useCallback } from 'react';
import { fileService } from '../services/fileService';
import { FileReference, SearchParams, PaginatedResponse } from '../types/file';
import {
  DocumentIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  Bars3BottomLeftIcon,
  Bars3BottomRightIcon,
  CheckIcon,
  DocumentDuplicateIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SearchBar } from './SearchBar';
import { FilterPanel } from './FilterPanel';
import { Pagination } from './Pagination';

export const FileList: React.FC = () => {
  const queryClient = useQueryClient();
  
  // State management
  const [searchParams, setSearchParams] = useState<SearchParams>({
    page: 1,
    page_size: 20,
    sort_by: '-uploaded_at'
  });
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [isSelectMode, setIsSelectMode] = useState(false);

  // Query for fetching files with pagination and filtering
  const { data: fileResponse, isLoading, error } = useQuery<PaginatedResponse<FileReference>>({
    queryKey: ['files', searchParams],
    queryFn: () => fileService.getFiles(searchParams),
    placeholderData: (previousData) => previousData,
  });

  // Mutations
  const deleteMutation = useMutation({
    mutationFn: fileService.deleteFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['storage-stats'] });
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: fileService.bulkDeleteFiles,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['storage-stats'] });
      setSelectedFiles(new Set());
      setIsSelectMode(false);
    },
  });

  const downloadMutation = useMutation({
    mutationFn: ({ fileUrl, filename }: { fileUrl: string; filename: string }) =>
      fileService.downloadFile(fileUrl, filename),
  });

  // Event handlers
  const handleSearch = useCallback((query: string) => {
    setSearchParams(prev => ({ 
      ...prev, 
      search: query || undefined, 
      page: 1 
    }));
  }, []);

  const handleFiltersChange = useCallback((filters: SearchParams) => {
    setSearchParams(prev => ({ 
      ...prev, 
      ...filters, 
      page: 1 
    }));
  }, []);

  const handleSort = useCallback((sortBy: string) => {
    setSearchParams(prev => ({ 
      ...prev, 
      sort_by: sortBy, 
      page: 1 
    }));
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setSearchParams(prev => ({ ...prev, page }));
  }, []);

  const handlePageSizeChange = useCallback((pageSize: number) => {
    setSearchParams(prev => ({ 
      ...prev, 
      page_size: pageSize, 
      page: 1 
    }));
  }, []);

  const handleFileSelect = (fileId: string) => {
    const newSelection = new Set(selectedFiles);
    if (newSelection.has(fileId)) {
      newSelection.delete(fileId);
    } else {
      newSelection.add(fileId);
    }
    setSelectedFiles(newSelection);
  };

  const handleSelectAll = () => {
    if (!fileResponse?.results) return;
    
    const allIds = fileResponse.results.map(file => file.id);
    const newSelection = new Set(selectedFiles);
    const allSelected = allIds.every(id => newSelection.has(id));
    
    if (allSelected) {
      allIds.forEach(id => newSelection.delete(id));
    } else {
      allIds.forEach(id => newSelection.add(id));
    }
    setSelectedFiles(newSelection);
  };

  const handleBulkDelete = async () => {
    if (selectedFiles.size === 0) return;
    
    if (!window.confirm(`Are you sure you want to delete ${selectedFiles.size} file(s)?`)) {
      return;
    }
    
    try {
      await bulkDeleteMutation.mutateAsync(Array.from(selectedFiles));
    } catch (err) {
      console.error('Bulk delete error:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this file?')) {
      return;
    }
    
    try {
      await deleteMutation.mutateAsync(id);
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const handleDownload = async (fileUrl: string, filename: string) => {
    try {
      await downloadMutation.mutateAsync({ fileUrl, filename });
    } catch (err) {
      console.error('Download error:', err);
    }
  };

  // Helper functions
  const getSortDirection = (field: string) => {
    if (searchParams.sort_by === field) return 'asc';
    if (searchParams.sort_by === `-${field}`) return 'desc';
    return 'none';
  };

  const toggleSort = (field: string) => {
    const currentDirection = getSortDirection(field);
    let newSort: string;
    
    if (currentDirection === 'none') {
      newSort = `-${field}`; // Start with descending
    } else if (currentDirection === 'desc') {
      newSort = field; // Switch to ascending
    } else {
      newSort = `-${field}`; // Switch back to descending
    }
    
    handleSort(newSort);
  };

  const totalPages = fileResponse ? Math.ceil(fileResponse.count / (searchParams.page_size || 20)) : 0;
  const currentPage = searchParams.page || 1;

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">Failed to load files. Please try again.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Search and Filter Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="space-y-4">
          {/* Search Bar */}
          <div>
            <h2 className="text-lg font-medium text-gray-900 mb-3">Search Files</h2>
            <SearchBar 
              onSearch={handleSearch}
              placeholder="Search by filename..."
              initialValue={searchParams.search || ''}
            />
          </div>
          
          {/* Filter Panel */}
          <FilterPanel 
            onFiltersChange={handleFiltersChange}
            activeFilters={searchParams}
          />
        </div>
      </div>

      {/* File List Section */}
      <div className="bg-white rounded-lg shadow">
        {/* Header with actions */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center space-x-4">
              <h2 className="text-lg font-medium text-gray-900">
                Files ({fileResponse?.count || 0})
              </h2>
              
              {/* Select Mode Toggle */}
              <button
                onClick={() => {
                  setIsSelectMode(!isSelectMode);
                  setSelectedFiles(new Set());
                }}
                className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  isSelectMode
                    ? 'bg-primary-100 text-primary-700 hover:bg-primary-200'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {isSelectMode ? (
                  <>
                    <EyeSlashIcon className="h-4 w-4 mr-1" />
                    Exit Select
                  </>
                ) : (
                  <>
                    <EyeIcon className="h-4 w-4 mr-1" />
                    Select
                  </>
                )}
              </button>
            </div>

            {/* Bulk Actions */}
            {isSelectMode && selectedFiles.size > 0 && (
              <div className="mt-3 sm:mt-0 flex items-center space-x-3">
                <span className="text-sm text-gray-600">
                  {selectedFiles.size} selected
                </span>
                <button
                  onClick={handleBulkDelete}
                  disabled={bulkDeleteMutation.isPending}
                  className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                >
                  <TrashIcon className="h-4 w-4 mr-1" />
                  Delete Selected
                </button>
              </div>
            )}
          </div>

          {/* Sort Controls */}
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="text-sm text-gray-600">Sort by:</span>
            {[
              { label: 'Name', field: 'original_filename' },
              { label: 'Size', field: 'size' },
              { label: 'Date', field: 'uploaded_at' },
              { label: 'Type', field: 'file_type' },
              { label: 'References', field: 'reference_count' }
            ].map(({ label, field }) => {
              const direction = getSortDirection(field);
              return (
                <button
                  key={field}
                  onClick={() => toggleSort(field)}
                  className={`inline-flex items-center px-2 py-1 rounded text-sm transition-colors ${
                    direction !== 'none'
                      ? 'bg-primary-100 text-primary-700 hover:bg-primary-200'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {label}
                  {direction === 'desc' && <Bars3BottomLeftIcon className="h-3 w-3 ml-1" />}
                  {direction === 'asc' && <Bars3BottomRightIcon className="h-3 w-3 ml-1" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* File List Content */}
        <div className="divide-y divide-gray-200">
          {isLoading ? (
            <div className="p-6">
              <div className="animate-pulse space-y-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="flex items-center space-x-4">
                    <div className="h-4 w-4 bg-gray-200 rounded"></div>
                    <div className="h-8 w-8 bg-gray-200 rounded"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                    </div>
                    <div className="flex space-x-2">
                      <div className="h-8 w-20 bg-gray-200 rounded"></div>
                      <div className="h-8 w-16 bg-gray-200 rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : !fileResponse?.results || fileResponse.results.length === 0 ? (
            <div className="text-center py-12">
              <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No files found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchParams.search || Object.keys(searchParams).some(k => k !== 'page' && k !== 'page_size' && k !== 'sort_by')
                  ? 'Try adjusting your search or filters'
                  : 'Get started by uploading a file'
                }
              </p>
            </div>
          ) : (
            fileResponse.results.map((file) => (
              <div key={file.id} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center space-x-4">
                  {/* Selection Checkbox */}
                  {isSelectMode && (
                    <div className="flex-shrink-0">
                      <button
                        onClick={() => handleFileSelect(file.id)}
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                          selectedFiles.has(file.id)
                            ? 'bg-primary-600 border-primary-600'
                            : 'border-gray-300 hover:border-gray-400'
                        }`}
                      >
                        {selectedFiles.has(file.id) && (
                          <CheckIcon className="h-3 w-3 text-white" />
                        )}
                      </button>
                    </div>
                  )}

                  {/* File Icon */}
                  <div className="flex-shrink-0 relative">
                    <DocumentIcon className="h-8 w-8 text-gray-400" />
                    {file.is_duplicate && (
                      <DocumentDuplicateIcon className="absolute -top-1 -right-1 h-4 w-4 text-amber-500" />
                    )}
                  </div>

                  {/* File Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.original_filename}
                      </p>
                      {file.reference_count > 1 && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                          {file.reference_count}x
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-3 text-sm text-gray-500">
                      <span>{file.file_type}</span>
                      <span>•</span>
                      <span>{fileService.formatFileSize(file.size)}</span>
                      <span>•</span>
                      <span>{fileService.formatDate(file.uploaded_at)}</span>
                      {file.is_duplicate && (
                        <>
                          <span>•</span>
                          <span className="text-amber-600">Duplicate</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  {!isSelectMode && (
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleDownload(file.file_url, file.original_filename)}
                        disabled={downloadMutation.isPending}
                        className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                        Download
                      </button>
                      <button
                        onClick={() => handleDelete(file.id)}
                        disabled={deleteMutation.isPending}
                        className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                      >
                        <TrashIcon className="h-4 w-4 mr-1" />
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {fileResponse && fileResponse.count > 0 && (
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={fileResponse.count}
            pageSize={searchParams.page_size || 20}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            isLoading={isLoading}
          />
        )}
      </div>

      {/* Select All in List Mode */}
      {isSelectMode && fileResponse?.results && fileResponse.results.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <button
            onClick={handleSelectAll}
            className="text-sm text-primary-600 hover:text-primary-500 font-medium"
          >
            {fileResponse.results.every(file => selectedFiles.has(file.id))
              ? 'Deselect All'
              : 'Select All on This Page'
            }
          </button>
        </div>
      )}
    </div>
  );
}; 