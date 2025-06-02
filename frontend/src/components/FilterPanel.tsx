import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fileService } from '../services/fileService';
import { SearchParams } from '../types/file';
import {
  FunnelIcon,
  XMarkIcon,
  DocumentIcon,
  CalendarIcon,
  ScaleIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';

interface FilterPanelProps {
  onFiltersChange: (filters: SearchParams) => void;
  activeFilters: SearchParams;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  onFiltersChange,
  activeFilters
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<SearchParams>(activeFilters);

  // Get available file types
  const { data: fileTypes = [] } = useQuery({
    queryKey: ['file-types'],
    queryFn: fileService.getFileTypes,
  });

  useEffect(() => {
    setLocalFilters(activeFilters);
  }, [activeFilters]);

  const handleFilterChange = (key: keyof SearchParams, value: any) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleFileTypeToggle = (fileType: string) => {
    const currentTypes = localFilters.file_type || [];
    const newTypes = currentTypes.includes(fileType)
      ? currentTypes.filter(t => t !== fileType)
      : [...currentTypes, fileType];
    
    handleFilterChange('file_type', newTypes.length > 0 ? newTypes : undefined);
  };

  const clearAllFilters = () => {
    const clearedFilters: SearchParams = {
      // Preserve pagination and sorting
      page: localFilters.page || 1,
      page_size: localFilters.page_size,
      sort_by: localFilters.sort_by,
      // Clear all filter-specific properties
      search: undefined,
      file_type: undefined,
      min_size: undefined,
      max_size: undefined,
      from_date: undefined,
      to_date: undefined,
      duplicates_only: undefined
    };
    setLocalFilters(clearedFilters);
    onFiltersChange(clearedFilters);
  };

  const removeFilter = (key: keyof SearchParams) => {
    const newFilters = { ...localFilters };
    (newFilters as any)[key] = undefined;
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const getActiveFilterCount = () => {
    let count = 0;
    if (localFilters.file_type?.length) count++;
    if (localFilters.min_size !== undefined || localFilters.max_size !== undefined) count++;
    if (localFilters.from_date || localFilters.to_date) count++;
    if (localFilters.duplicates_only) count++;
    return count;
  };

  const formatFileSize = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${Math.round(size)} ${units[unitIndex]}`;
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200">
      {/* Filter Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center">
          <FunnelIcon className="h-5 w-5 text-gray-600 mr-2" />
          <h3 className="text-sm font-medium text-gray-900">Filters</h3>
          {getActiveFilterCount() > 0 && (
            <span className="ml-2 bg-primary-100 text-primary-800 text-xs font-medium px-2 py-1 rounded-full">
              {getActiveFilterCount()}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {getActiveFilterCount() > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                clearAllFilters();
              }}
              className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100"
            >
              Clear all
            </button>
          )}
          {isExpanded ? (
            <ChevronUpIcon className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </div>

      {/* Active Filters Display */}
      {getActiveFilterCount() > 0 && (
        <div className="px-4 pb-3">
          <div className="flex flex-wrap gap-2">
            {localFilters.file_type?.map(type => (
              <span key={type} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
                {type}
                <button
                  onClick={() => handleFileTypeToggle(type)}
                  className="ml-1 hover:text-blue-600"
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            ))}
            
            {(localFilters.min_size !== undefined || localFilters.max_size !== undefined) && (
              <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800">
                Size: {localFilters.min_size ? formatFileSize(localFilters.min_size) : '0'} - {localFilters.max_size ? formatFileSize(localFilters.max_size) : '∞'}
                <button
                  onClick={() => {
                    const newFilters = { ...localFilters };
                    newFilters.min_size = undefined;
                    newFilters.max_size = undefined;
                    setLocalFilters(newFilters);
                    onFiltersChange(newFilters);
                  }}
                  className="ml-1 hover:text-green-600"
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            )}
            
            {(localFilters.from_date || localFilters.to_date) && (
              <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800">
                Date Range
                <button
                  onClick={() => {
                    const newFilters = { ...localFilters };
                    newFilters.from_date = undefined;
                    newFilters.to_date = undefined;
                    setLocalFilters(newFilters);
                    onFiltersChange(newFilters);
                  }}
                  className="ml-1 hover:text-purple-600"
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            )}
            
            {localFilters.duplicates_only && (
              <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-amber-100 text-amber-800">
                Duplicates Only
                <button
                  onClick={() => removeFilter('duplicates_only')}
                  className="ml-1 hover:text-amber-600"
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Filter Controls */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-4 space-y-6">
          {/* File Type Filter */}
          <div>
            <div className="flex items-center mb-3">
              <DocumentIcon className="h-4 w-4 text-gray-600 mr-2" />
              <label className="text-sm font-medium text-gray-700">File Types</label>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {fileTypes.map(type => (
                <label key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={localFilters.file_type?.includes(type) || false}
                    onChange={() => handleFileTypeToggle(type)}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="ml-2 text-xs text-gray-600 truncate">{type}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Size Range Filter */}
          <div>
            <div className="flex items-center mb-3">
              <ScaleIcon className="h-4 w-4 text-gray-600 mr-2" />
              <label className="text-sm font-medium text-gray-700">File Size</label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Min Size (bytes)</label>
                <input
                  type="number"
                  value={localFilters.min_size || ''}
                  onChange={(e) => handleFilterChange('min_size', e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Max Size (bytes)</label>
                <input
                  type="number"
                  value={localFilters.max_size || ''}
                  onChange={(e) => handleFilterChange('max_size', e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="No limit"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>
          </div>

          {/* Date Range Filter */}
          <div>
            <div className="flex items-center mb-3">
              <CalendarIcon className="h-4 w-4 text-gray-600 mr-2" />
              <label className="text-sm font-medium text-gray-700">Upload Date</label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">From</label>
                <input
                  type="date"
                  value={localFilters.from_date || ''}
                  onChange={(e) => handleFilterChange('from_date', e.target.value || undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">To</label>
                <input
                  type="date"
                  value={localFilters.to_date || ''}
                  onChange={(e) => handleFilterChange('to_date', e.target.value || undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>
          </div>

          {/* Duplicates Only Filter */}
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={localFilters.duplicates_only || false}
                onChange={(e) => handleFilterChange('duplicates_only', e.target.checked || undefined)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">Show duplicates only</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}; 