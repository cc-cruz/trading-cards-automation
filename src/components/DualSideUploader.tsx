import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'react-hot-toast';
import Image from 'next/image';
import { FileUploadState, CardProcessingResult, UploadStep, UploadMode } from '@/types';

interface DualSideUploaderProps {
  selectedCollection: string;
  onCardProcessed: (result: CardProcessingResult) => void;
  onError: (error: string) => void;
}

const UPLOAD_MODES: UploadMode[] = [
  {
    type: 'auto',
    description: 'Smart detection (recommended)',
    confidence_boost: 'Automatically uses dual-side for best results'
  },
  {
    type: 'dual',
    description: 'Dual-side (front + back)',
    confidence_boost: '+40% accuracy improvement'
  },
  {
    type: 'single',
    description: 'Single-side (front only)',
    confidence_boost: 'Basic processing'
  }
];

export default function DualSideUploader({ selectedCollection, onCardProcessed, onError }: DualSideUploaderProps) {
  const { user } = useAuth();
  const [mode, setMode] = useState<'auto' | 'dual' | 'single'>('auto');
  const [files, setFiles] = useState<FileUploadState[]>([]);
  const [processing, setProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<UploadStep[]>([]);

  // Initialize upload steps
  const initializeSteps = (isDual: boolean): UploadStep[] => [
    { step: 'select', description: 'Select files', status: 'completed' },
    { step: 'upload', description: `Upload to cloud storage`, status: 'pending' },
    { step: 'process', description: `${isDual ? 'Dual-side' : 'Single-side'} OCR processing`, status: 'pending' },
    { step: 'complete', description: 'Add to collection', status: 'pending' }
  ];

  // Smart file detection - suggest dual-side if user drops paired files
  const detectUploadMode = (newFiles: File[]): 'single' | 'dual' => {
    if (newFiles.length === 2) {
      const names = newFiles.map(f => f.name.toLowerCase());
      const hasFrontBack = names.some(name => 
        name.includes('front') || name.includes('back') || 
        name.includes('_f') || name.includes('_b')
      );
      if (hasFrontBack) return 'dual';
    }
    return newFiles.length > 1 ? 'dual' : 'single';
  };

  const createFileState = (file: File, side: 'front' | 'back' = 'front'): FileUploadState => ({
    id: Math.random().toString(36).substr(2, 9),
    file,
    preview: URL.createObjectURL(file),
    side,
    upload_status: 'pending',
    upload_progress: 0
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (!selectedCollection) {
      toast.error('Please select a collection first');
      return;
    }

    const newFiles = acceptedFiles.map((file, index) => {
      // Smart side detection
      const fileName = file.name.toLowerCase();
      let side: 'front' | 'back' = 'front';
      
      if (fileName.includes('back') || fileName.includes('_b')) {
        side = 'back';
      } else if (fileName.includes('front') || fileName.includes('_f')) {
        side = 'front';
      } else if (acceptedFiles.length === 2 && index === 1) {
        side = 'back';
      }

      return createFileState(file, side);
    });

    setFiles(prev => [...prev, ...newFiles]);

    // Auto-suggest mode based on files
    if (mode === 'auto') {
      const suggestedMode = detectUploadMode(acceptedFiles);
      if (suggestedMode === 'dual' && acceptedFiles.length === 2) {
        toast.success('Great! Dual-side upload detected. This will improve accuracy by ~40%!', { duration: 4000 });
      }
    }
  }, [selectedCollection, mode]);

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
  };

  const updateFileProgress = (fileId: string, progress: number, status?: FileUploadState['upload_status']) => {
    setFiles(prev => prev.map(file => 
      file.id === fileId 
        ? { ...file, upload_progress: progress, ...(status && { upload_status: status }) }
        : file
    ));
  };

  const uploadToGCS = async (file: File, signedUrl: string, fileId: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const progress = (event.loaded / event.total) * 100;
          updateFileProgress(fileId, progress, 'uploading');
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          updateFileProgress(fileId, 100, 'uploaded');
          resolve(signedUrl.split('?')[0]); // Return public URL
        } else {
          updateFileProgress(fileId, 0, 'failed');
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      };

      xhr.onerror = () => {
        updateFileProgress(fileId, 0, 'failed');
        reject(new Error('Upload failed'));
      };

      xhr.open('PUT', signedUrl);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  };

  const processFiles = async () => {
    if (files.length === 0) return;
    
    setProcessing(true);
    const token = localStorage.getItem('token');
    
    try {
      // Determine processing mode
      const isDualSide = mode === 'dual' || (mode === 'auto' && files.length >= 2);
      setCurrentStep(initializeSteps(isDualSide));

      if (isDualSide && files.length >= 2) {
        await processDualSide(files.slice(0, 2), token!);
      } else {
        await processSingleSide(files[0], token!);
      }
    } catch (error) {
      console.error('Processing failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      onError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setProcessing(false);
    }
  };

  const updateStepStatus = (step: UploadStep['step'], status: UploadStep['status'], error?: string) => {
    setCurrentStep(prev => prev.map(s => 
      s.step === step ? { ...s, status, error } : s
    ));
  };

  const processDualSide = async (fileStates: FileUploadState[], token: string) => {
    const [frontFile, backFile] = fileStates;
    
    // Step 1: Get signed URLs
    updateStepStatus('upload', 'active');
    const urlResponse = await fetch('/api/v1/uploads/signed-urls-dual', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content_type: frontFile.file.type,
        front_filename: frontFile.file.name,
        back_filename: backFile?.file.name
      })
    });

    if (!urlResponse.ok) {
      throw new Error('Failed to get upload URLs');
    }

    const urls = await urlResponse.json();

    // Step 2: Upload files to GCS
    const [frontUrl, backUrl] = await Promise.all([
      uploadToGCS(frontFile.file, urls.front.upload_url, frontFile.id),
      backFile ? uploadToGCS(backFile.file, urls.back.upload_url, backFile.id) : Promise.resolve(undefined)
    ]);

    updateStepStatus('upload', 'completed');

    // Step 3: Process with dual-side OCR
    updateStepStatus('process', 'active');
    const processResponse = await fetch('/api/v1/cards/process-dual-side', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        front_image_url: frontUrl,
        back_image_url: backUrl,
        collection_id: selectedCollection,
        filename: frontFile.file.name
      })
    });

    if (!processResponse.ok) {
      throw new Error('Failed to process card');
    }

    const result = await processResponse.json();
    updateStepStatus('process', 'completed');
    updateStepStatus('complete', 'completed');

    onCardProcessed(result);
    toast.success(`Card processed with ${(result.card_data.confidence_score * 100).toFixed(0)}% confidence!`);
  };

  const processSingleSide = async (fileState: FileUploadState, token: string) => {
    // Step 1: Get signed URL
    updateStepStatus('upload', 'active');
    const urlResponse = await fetch('/api/v1/uploads/signed-url', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content_type: fileState.file.type,
        filename: fileState.file.name
      })
    });

    if (!urlResponse.ok) {
      throw new Error('Failed to get upload URL');
    }

    const urlData = await urlResponse.json();

    // Step 2: Upload file to GCS
    const publicUrl = await uploadToGCS(fileState.file, urlData.upload_url, fileState.id);
    updateStepStatus('upload', 'completed');

    // Step 3: Process with single-side OCR
    updateStepStatus('process', 'active');
    const processResponse = await fetch('/api/v1/cards/process-url', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image_url: publicUrl,
        collection_id: selectedCollection,
        filename: fileState.file.name
      })
    });

    if (!processResponse.ok) {
      throw new Error('Failed to process card');
    }

    const result = await processResponse.json();
    updateStepStatus('process', 'completed');
    updateStepStatus('complete', 'completed');

    onCardProcessed(result);
    toast.success(`Card processed with ${(result.card_data.confidence_score * 100).toFixed(0)}% confidence!`);
  };

  const clearAll = () => {
    files.forEach(file => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview);
      }
    });
    setFiles([]);
    setCurrentStep([]);
  };

  // Get file pairs for dual-side display
  const getFilePairs = () => {
    const frontFiles = files.filter(f => f.side === 'front');
    const backFiles = files.filter(f => f.side === 'back');
    
    if (mode === 'dual') {
      return frontFiles.map(front => ({
        front,
        back: backFiles.find(back => back.paired_with === front.id) || null
      }));
    }
    
    return files.map(file => ({ front: file, back: null }));
  };

  return (
    <div className="space-y-6">
      {/* Mode Selection */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Upload Mode</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {UPLOAD_MODES.map((uploadMode) => (
            <button
              key={uploadMode.type}
              onClick={() => setMode(uploadMode.type)}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                mode === uploadMode.type
                  ? 'border-blue-500 bg-blue-50 text-blue-900'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="font-medium">{uploadMode.description}</div>
              <div className="text-sm text-gray-600 mt-1">{uploadMode.confidence_boost}</div>
            </button>
          ))}
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
          <div className="text-6xl text-gray-400">
            {mode === 'dual' ? '🃏🔄' : '📸'}
          </div>
          {isDragActive ? (
            <p className="text-xl text-blue-600">Drop the card images here...</p>
          ) : (
            <>
              <p className="text-xl text-gray-600">
                {mode === 'dual' 
                  ? 'Drop front and back images of your card'
                  : 'Drag & drop card images here, or click to select'
                }
              </p>
              <p className="text-sm text-gray-500">
                Supports JPG, PNG, GIF, BMP, WebP (max 10MB each)
              </p>
            </>
          )}
        </div>
      </div>

      {/* Progress Steps */}
      {currentStep.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h4 className="font-medium text-gray-900 mb-3">Processing Steps</h4>
          <div className="space-y-2">
            {currentStep.map((step, index) => (
              <div key={step.step} className="flex items-center space-x-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                  step.status === 'completed' ? 'bg-green-100 text-green-800' :
                  step.status === 'active' ? 'bg-blue-100 text-blue-800' :
                  step.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-500'
                }`}>
                  {step.status === 'completed' ? '✓' : 
                   step.status === 'active' ? '●' :
                   step.status === 'failed' ? '✗' : index + 1}
                </div>
                <span className={`text-sm ${
                  step.status === 'failed' ? 'text-red-600' : 'text-gray-700'
                }`}>
                  {step.description}
                </span>
                {step.status === 'active' && (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* File Preview */}
      {files.length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900">
              Selected Images ({files.length})
            </h3>
            <div className="space-x-2">
              <button
                onClick={processFiles}
                disabled={!selectedCollection || processing || files.length === 0}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing ? 'Processing...' : 'Process Cards'}
              </button>
              <button
                onClick={clearAll}
                disabled={processing}
                className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 disabled:opacity-50"
              >
                Clear All
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {getFilePairs().map((pair, index) => (
              <div key={`pair-${index}`} className="bg-gray-50 rounded-lg p-4">
                {mode === 'dual' ? (
                  <div className="space-y-3">
                    {/* Front Image */}
                    <div className="relative">
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Front</label>
                      {pair.front.preview && (
                        <Image
                          src={pair.front.preview}
                          alt="Front"
                          width={200}
                          height={280}
                          className="w-full h-32 object-cover rounded-md"
                        />
                      )}
                      <button
                        onClick={() => removeFile(pair.front.id)}
                        className="absolute top-6 right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-red-700"
                      >
                        ×
                      </button>
                      {/* Upload Progress */}
                      {pair.front.upload_status === 'uploading' && (
                        <div className="absolute bottom-1 left-1 right-1 bg-black bg-opacity-50 rounded">
                          <div 
                            className="bg-blue-500 h-1 rounded transition-all duration-300"
                            style={{ width: `${pair.front.upload_progress}%` }}
                          />
                        </div>
                      )}
                    </div>

                    {/* Back Image */}
                    <div className="relative">
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Back</label>
                      {pair.back ? (
                        <>
                          <Image
                            src={pair.back.preview}
                            alt="Back"
                            width={200}
                            height={280}
                            className="w-full h-32 object-cover rounded-md"
                          />
                          <button
                            onClick={() => removeFile(pair.back!.id)}
                            className="absolute top-6 right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-red-700"
                          >
                            ×
                          </button>
                          {pair.back.upload_status === 'uploading' && (
                            <div className="absolute bottom-1 left-1 right-1 bg-black bg-opacity-50 rounded">
                              <div 
                                className="bg-blue-500 h-1 rounded transition-all duration-300"
                                style={{ width: `${pair.back.upload_progress}%` }}
                              />
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="w-full h-32 border-2 border-dashed border-gray-300 rounded-md flex items-center justify-center text-gray-400">
                          <span className="text-sm">Drop back image here</span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  /* Single Image Display */
                  <div className="relative">
                    <Image
                      src={pair.front.preview}
                      alt={pair.front.file.name}
                      width={300}
                      height={400}
                      className="w-full h-48 object-cover rounded-md"
                    />
                    <button
                      onClick={() => removeFile(pair.front.id)}
                      className="absolute top-2 right-2 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm hover:bg-red-700"
                    >
                      ×
                    </button>
                    {pair.front.upload_status === 'uploading' && (
                      <div className="absolute bottom-2 left-2 right-2 bg-black bg-opacity-50 rounded">
                        <div 
                          className="bg-blue-500 h-2 rounded transition-all duration-300"
                          style={{ width: `${pair.front.upload_progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                )}
                
                <div className="mt-3">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {pair.front.file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(pair.front.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Help Text */}
      <div className="bg-blue-50 rounded-lg p-4">
        <h4 className="font-semibold text-blue-900 mb-2">💡 Pro Tips:</h4>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li><strong>Dual-side mode:</strong> Upload both front and back for 40% better accuracy</li>
          <li><strong>Card numbers and years</strong> are usually found on the back side</li>
          <li><strong>Set names and parallels</strong> are typically clearer on the front</li>
          <li><strong>Auto mode:</strong> Automatically detects the best processing method</li>
        </ul>
      </div>
    </div>
  );
} 