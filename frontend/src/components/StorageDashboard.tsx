import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fileService } from '../services/fileService';
import { 
  ChartBarIcon, 
  CloudIcon, 
  DocumentDuplicateIcon, 
  CheckCircleIcon 
} from '@heroicons/react/24/outline';

export const StorageDashboard: React.FC = () => {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['storage-stats'],
    queryFn: fileService.getStorageStats,
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-600 text-center">
          Failed to load storage statistics
        </div>
      </div>
    );
  }

  if (!stats) return null;

  const statCards = [
    {
      title: 'Total Files',
      value: stats.total_files_uploaded.toLocaleString(),
      subtitle: `${stats.unique_files_stored} unique`,
      icon: DocumentDuplicateIcon,
      color: 'bg-blue-500',
    },
    {
      title: 'Storage Saved',
      value: `${stats.storage_saved_mb.toFixed(1)} MB`,
      subtitle: `${stats.savings_percentage.toFixed(1)}% savings`,
      icon: CheckCircleIcon,
      color: 'bg-green-500',
    },
    {
      title: 'Deduplication',
      value: `${stats.deduplication_ratio.toFixed(2)}:1`,
      subtitle: 'efficiency ratio',
      icon: ChartBarIcon,
      color: 'bg-purple-500',
    },
    {
      title: 'Total Storage',
      value: `${stats.actual_size_stored_mb.toFixed(1)} MB`,
      subtitle: `of ${stats.total_size_uploaded_mb.toFixed(1)} MB uploaded`,
      icon: CloudIcon,
      color: 'bg-orange-500',
    },
  ];

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center mb-6">
        <ChartBarIcon className="h-6 w-6 text-primary-600 mr-2" />
        <h2 className="text-xl font-semibold text-gray-900">Storage Dashboard</h2>
        <span className="ml-auto text-sm text-gray-500">
          Last updated: {fileService.formatDate(stats.last_updated)}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {statCards.map((card, index) => (
          <div key={index} className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center">
              <div className={`${card.color} p-2 rounded-lg mr-3`}>
                <card.icon className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-600">{card.title}</p>
                <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                <p className="text-xs text-gray-500">{card.subtitle}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Storage efficiency visualization */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Storage Breakdown</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Actual Storage Used</span>
              <span className="font-medium">{stats.actual_size_stored_mb.toFixed(1)} MB</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Storage Saved</span>
              <span className="font-medium text-green-600">
                {stats.storage_saved_mb.toFixed(1)} MB
              </span>
            </div>
            <div className="flex justify-between text-sm border-t pt-2">
              <span className="font-medium">Total Uploaded</span>
              <span className="font-medium">{stats.total_size_uploaded_mb.toFixed(1)} MB</span>
            </div>
          </div>
          
          {/* Progress bar visualization */}
          <div className="mt-4">
            <div className="flex text-xs text-gray-600 mb-1">
              <span>Storage Efficiency</span>
              <span className="ml-auto">{stats.savings_percentage.toFixed(1)}% saved</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-green-500 h-2 rounded-full transition-all duration-500" 
                style={{ width: `${stats.savings_percentage}%` }}
              ></div>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Deduplication Impact</h3>
          <div className="space-y-3">
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">
                {((stats.total_files_uploaded - stats.unique_files_stored) / stats.total_files_uploaded * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">files were duplicates</div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-center text-sm">
              <div>
                <div className="text-lg font-semibold text-gray-900">
                  {stats.total_files_uploaded - stats.unique_files_stored}
                </div>
                <div className="text-gray-600">duplicates found</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-gray-900">
                  {stats.unique_files_stored}
                </div>
                <div className="text-gray-600">unique files</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}; 