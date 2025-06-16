import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'react-hot-toast';
import Image from 'next/image';

interface UploadedFile extends File {
  preview?: string;
  id: string;
}

interface CardData {
  player: string;
  set: string;
  year: string;
  card_number: string;
  parallel: string;
  manufacturer: string;
  features: string;
  graded: boolean;
  grade: string;
  grading_company: string;
  cert_number: string;
}

interface ProcessingResult {
  file_id: string;
  status: 'processing' | 'completed' | 'error';
  card_data?: CardData;
  price_data?: any;
  error?: string;
}

export default function Upload() {
  const { user } = useAuth();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [processing, setProcessing] = useState<{[key: string]: ProcessingResult}>({});
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [collections, setCollections] = useState<any[]>([]);

  // Create object URLs for preview and cleanup
  const createFilePreview = (file: File): UploadedFile => {
    const fileWithPreview = Object.assign(file, {
      preview: URL.createObjectURL(file),
      id: Math.random().toString(36).substr(2, 9)
    });
    return fileWithPreview;
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(createFilePreview);
    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.bmp', '.webp']
    },
    multiple: true,
    maxSize: 10 * 1024 * 1024 // 10MB
  });

  const removeFile = (fileId: string) => {
    setFiles(prev => {
      const fileToRemove = prev.find(f => f.id === fileId);
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview);
      }
      return prev.filter(f => f.id !== fileId);
    });
    setProcessing(prev => {
      const newProcessing = { ...prev };
      delete newProcessing[fileId];
      return newProcessing;
    });
  };

  const processFiles = async () => {
    if (files.length === 0) {
      toast('Please select at least one image', { icon: '❌' });
      return;
    }

    if (!selectedCollection) {
      toast('Please select a collection', { icon: '❌' });
      return;
    }

    // Initialize processing states
    const initialProcessing: {[key: string]: ProcessingResult} = {};
    files.forEach(file => {
      initialProcessing[file.id] = {
        file_id: file.id,
        status: 'processing'
      };
    });
    setProcessing(initialProcessing);

    // Process each file
    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('collection_id', selectedCollection);

        const response = await fetch('/api/v1/cards/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        });

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }

        const result = await response.json();
        
        setProcessing(prev => ({
          ...prev,
          [file.id]: {
            file_id: file.id,
            status: 'completed',
            card_data: result.card_data,
            price_data: result.price_data
          }
        }));

        toast(`Successfully processed ${file.name}`, { icon: '✅' });

      } catch (error) {
        console.error('Error processing file:', error);
        setProcessing(prev => ({
          ...prev,
          [file.id]: {
            file_id: file.id,
            status: 'error',
            error: error instanceof Error ? error.message : 'Unknown error'
          }
        }));
        toast(`Failed to process ${file.name}`, { icon: '❌' });
      }
    }
  };

  const clearAll = () => {
    files.forEach(file => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview);
      }
    });
    setFiles([]);
    setProcessing({});
  };

  // Load collections on mount
  React.useEffect(() => {
    const loadCollections = async () => {
      try {
        console.log('Loading collections...');
        const response = await fetch('/api/v1/collections', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        console.log('Collections response status:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Collections data:', data);
          setCollections(data);
          if (data.length > 0) {
            setSelectedCollection(data[0].id);
            console.log('Selected collection:', data[0].id);
          } else {
            console.log('No collections found - creating one...');
            // Create a default collection if none exist
            await createDefaultCollection();
          }
        } else {
          console.error('Failed to load collections:', response.status, response.statusText);
          toast('Failed to load collections', { icon: '❌' });
        }
      } catch (error) {
        console.error('Error loading collections:', error);
        toast('Error loading collections', { icon: '❌' });
      }
    };

    const createDefaultCollection = async () => {
      try {
        const response = await fetch('/api/v1/collections', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            name: 'My Cards',
            description: 'Default collection for your trading cards'
          })
        });
        
        if (response.ok) {
          const newCollection = await response.json();
          setCollections([newCollection]);
          setSelectedCollection(newCollection.id);
          toast('Created default collection', { icon: '✅' });
        }
      } catch (error) {
        console.error('Error creating default collection:', error);
      }
    };

    loadCollections();
  }, []);

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Upload Trading Cards</h1>
        
        {/* Collection Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Collection
          </label>
          <select
            value={selectedCollection}
            onChange={(e) => setSelectedCollection(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Choose a collection...</option>
            {collections.map((collection) => (
              <option key={collection.id} value={collection.id}>
                {collection.name}
              </option>
            ))}
          </select>
          
          {/* Debug info */}
          <div className="mt-2 text-xs text-gray-500">
            Debug: Collections: {collections.length}, Selected: {selectedCollection || 'none'}
          </div>
        </div>

        {/* Upload Area */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
            ${isDragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 hover:border-gray-400'
            }`}
        >
          <input {...getInputProps()} />
          <div className="space-y-4">
            <div className="text-6xl text-gray-400">📸</div>
            {isDragActive ? (
              <p className="text-xl text-blue-600">Drop the card images here...</p>
            ) : (
              <>
                <p className="text-xl text-gray-600">
                  Drag & drop card images here, or click to select
                </p>
                <p className="text-sm text-gray-500">
                  Supports JPG, PNG, GIF, BMP, WebP (max 10MB each)
                </p>
              </>
            )}
          </div>
        </div>

        {/* File Preview Grid */}
        {files.length > 0 && (
          <div className="mt-8">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Selected Images ({files.length})
              </h3>
              <div className="space-x-2">
                <button
                  onClick={processFiles}
                  disabled={!selectedCollection || Object.keys(processing).length > 0}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {Object.keys(processing).length > 0 ? 'Processing...' : 'Process Cards'}
                </button>
                <button
                  onClick={clearAll}
                  className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
                >
                  Clear All
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {files.map((file) => {
                const processingState = processing[file.id];
                return (
                  <div key={file.id} className="bg-gray-50 rounded-lg p-4">
                    <div className="relative">
                      {file.preview && (
                        <Image
                          src={file.preview}
                          alt={file.name}
                          width={300}
                          height={400}
                          className="w-full h-48 object-cover rounded-md"
                        />
                      )}
                      <button
                        onClick={() => removeFile(file.id)}
                        className="absolute top-2 right-2 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm hover:bg-red-700"
                      >
                        ×
                      </button>
                    </div>
                    
                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      
                      {/* Processing Status */}
                      {processingState && (
                        <div className="mt-2">
                          {processingState.status === 'processing' && (
                            <div className="flex items-center text-blue-600">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                              <span className="text-sm">Processing...</span>
                            </div>
                          )}
                          
                          {processingState.status === 'completed' && (
                            <div className="text-green-600">
                              <div className="flex items-center">
                                <span className="text-sm">✅ Completed</span>
                              </div>
                              {processingState.card_data && (
                                <div className="mt-2 text-xs text-gray-600">
                                  <p><strong>Player:</strong> {processingState.card_data.player}</p>
                                  <p><strong>Set:</strong> {processingState.card_data.set}</p>
                                  <p><strong>Year:</strong> {processingState.card_data.year}</p>
                                  {processingState.card_data.graded && (
                                    <p><strong>Grade:</strong> {processingState.card_data.grading_company} {processingState.card_data.grade}</p>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                          
                          {processingState.status === 'error' && (
                            <div className="text-red-600">
                              <span className="text-sm">❌ Error</span>
                              {processingState.error && (
                                <p className="text-xs mt-1">{processingState.error}</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Help Text */}
        <div className="mt-8 bg-blue-50 rounded-lg p-4">
          <h4 className="font-semibold text-blue-900 mb-2">How it works:</h4>
          <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
            <li>Select or create a collection for your cards</li>
            <li>Upload clear images of your trading cards</li>
            <li>Our OCR technology will extract card details automatically</li>
            <li>We'll research current market prices for your cards</li>
            <li>Review and edit the extracted information if needed</li>
            <li>Your cards will be added to your collection with pricing data</li>
          </ol>
        </div>
      </div>
    </div>
  );
} 