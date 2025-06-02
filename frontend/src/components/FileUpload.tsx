import React, { useState } from 'react';
import { fileService } from '../services/fileService';
import { 
  CloudArrowUpIcon, 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  DocumentDuplicateIcon 
} from '@heroicons/react/24/outline';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FileUploadResponse } from '../types/file';

interface FileUploadProps {
  onUploadSuccess: () => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<FileUploadResponse | null>(null);
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: fileService.uploadFile,
    onSuccess: (data: FileUploadResponse) => {
      // Invalidate and refetch queries
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['storage-stats'] });
      
      setSelectedFile(null);
      setUploadResult(data);
      onUploadSuccess();
      
      // Auto-clear success message after 5 seconds
      setTimeout(() => setUploadResult(null), 5000);
    },
    onError: (error) => {
      setError('Failed to upload file. Please try again.');
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      setError(null);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    try {
      setError(null);
      setUploadResult(null);
      setUploading(true);
      await uploadMutation.mutateAsync(selectedFile);
    } catch (error) {
      setError('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center mb-4">
        <CloudArrowUpIcon className="h-6 w-6 text-primary-600 mr-2" />
        <h2 className="text-xl font-semibold text-gray-900">Upload File</h2>
      </div>

      {/* Upload Success/Duplicate Notification */}
      {uploadResult && (
        <div className={`mb-4 p-4 rounded-lg border ${
          uploadResult.is_duplicate 
            ? 'bg-amber-50 border-amber-200' 
            : 'bg-green-50 border-green-200'
        }`}>
          <div className="flex items-start">
            {uploadResult.is_duplicate ? (
              <DocumentDuplicateIcon className="h-5 w-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0" />
            ) : (
              <CheckCircleIcon className="h-5 w-5 text-green-600 mt-0.5 mr-3 flex-shrink-0" />
            )}
            <div className="flex-1">
              <h3 className={`text-sm font-medium ${
                uploadResult.is_duplicate ? 'text-amber-800' : 'text-green-800'
              }`}>
                {uploadResult.is_duplicate ? 'Duplicate File Detected' : 'Upload Successful'}
              </h3>
              <p className={`mt-1 text-sm ${
                uploadResult.is_duplicate ? 'text-amber-700' : 'text-green-700'
              }`}>
                {uploadResult.message}
              </p>
              {uploadResult.is_duplicate && uploadResult.storage_saved > 0 && (
                <p className="mt-1 text-xs text-amber-600">
                  Storage saved: {fileService.formatFileSize(uploadResult.storage_saved)}
                </p>
              )}
              <div className="mt-2 text-xs text-gray-600">
                <span>File: {uploadResult.file_reference.original_filename}</span>
                <span className="mx-2">•</span>
                <span>Size: {fileService.formatFileSize(uploadResult.file_reference.size)}</span>
                <span className="mx-2">•</span>
                <span>References: {uploadResult.file_reference.reference_count}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 space-y-4">
        <div className="flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg">
          <div className="space-y-1 text-center">
            <div className="flex text-sm text-gray-600">
              <label
                htmlFor="file-upload"
                className="relative cursor-pointer bg-white rounded-md font-medium text-primary-600 hover:text-primary-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-primary-500"
              >
                <span>Upload a file</span>
                <input
                  id="file-upload"
                  name="file-upload"
                  type="file"
                  className="sr-only"
                  onChange={handleFileSelect}
                  disabled={uploading}
                />
              </label>
              <p className="pl-1">or drag and drop</p>
            </div>
            <p className="text-xs text-gray-500">Any file up to 10MB</p>
          </div>
        </div>

        {selectedFile && (
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-sm text-gray-700">
              <span className="font-medium">Selected:</span> {selectedFile.name}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Size: {fileService.formatFileSize(selectedFile.size)}
              <span className="mx-2">•</span>
              Type: {selectedFile.type || 'Unknown'}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
            <ExclamationTriangleIcon className="h-5 w-5 mr-2 flex-shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
          className={`w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white transition-colors ${
            !selectedFile || uploading
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500'
          }`}
        >
          {uploading ? (
            <>
              <svg
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Uploading...
            </>
          ) : (
            'Upload File'
          )}
        </button>
      </div>
    </div>
  );
}; 