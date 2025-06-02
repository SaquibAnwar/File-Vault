import React, { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { FileList } from './components/FileList';
import { StorageDashboard } from './components/StorageDashboard';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Abnormal File Vault</h1>
              <p className="mt-1 text-sm text-gray-600">
                Intelligent file management with deduplication
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="h-2 w-2 bg-green-400 rounded-full"></div>
              <span className="text-sm text-gray-600">System Online</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="space-y-6">
          {/* Storage Dashboard */}
          <StorageDashboard />

          {/* File Upload */}
          <div className="bg-white rounded-lg shadow">
            <FileUpload onUploadSuccess={handleUploadSuccess} />
          </div>

          {/* File List with Search and Filters */}
          <FileList key={refreshKey} />
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <p className="text-sm text-gray-500">
              © 2024 Abnormal File Vault. Powered by intelligent deduplication.
            </p>
            <div className="mt-2 sm:mt-0 flex items-center space-x-4 text-xs text-gray-400">
              <span>Phase 3: Complete</span>
              <span>•</span>
              <span>Enhanced UI</span>
              <span>•</span>
              <span>Search & Filters</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
