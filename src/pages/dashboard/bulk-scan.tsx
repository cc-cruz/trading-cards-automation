import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '../../contexts/AuthContext';
import Layout from '../../components/Layout';

interface ProcessingCard {
  id: string;
  file: File;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  result?: {
    player_name: string;
    set_name: string;
    year: string;
    estimated_value: number;
  };
  error?: string;
}

export default function BulkScan() {
  const { user } = useAuth();
  const [cards, setCards] = useState<ProcessingCard[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentCollection, setCurrentCollection] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newCards = acceptedFiles.map((file, index) => ({
      id: `${Date.now()}-${index}`,
      file,
      status: 'pending' as const,
      progress: 0,
    }));
    setCards(prev => [...prev, ...newCards]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.webp']
    },
    multiple: true,
    disabled: isProcessing
  });

  const processAllCards = async () => {
    if (cards.length === 0) return;
    
    setIsProcessing(true);
    
    for (let i = 0; i < cards.length; i++) {
      const card = cards[i];
      if (card.status !== 'pending') continue;

      // Update status to processing
      setCards(prev => prev.map(c => 
        c.id === card.id 
          ? { ...c, status: 'processing', progress: 10 }
          : c
      ));

      try {
        const formData = new FormData();
        formData.append('file', card.file);
        formData.append('collection_id', currentCollection || 'default');

        const response = await fetch('/api/v1/cards/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          
          setCards(prev => prev.map(c => 
            c.id === card.id 
              ? { 
                  ...c, 
                  status: 'completed', 
                  progress: 100,
                  result: {
                    player_name: result.card_data?.player || 'Unknown',
                    set_name: result.card_data?.set || 'Unknown Set',
                    year: result.card_data?.year || 'Unknown',
                    estimated_value: result.price_data?.estimated_value || 0
                  }
                }
              : c
          ));
        } else {
          throw new Error('Upload failed');
        }
      } catch (error) {
        setCards(prev => prev.map(c => 
          c.id === card.id 
            ? { 
                ...c, 
                status: 'error', 
                progress: 0,
                error: 'Failed to process card'
              }
            : c
        ));
      }

      // Small delay between uploads to prevent overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setIsProcessing(false);
  };

  const removeCard = (cardId: string) => {
    setCards(prev => prev.filter(c => c.id !== cardId));
  };

  const clearAll = () => {
    setCards([]);
  };

  const completedCards = cards.filter(c => c.status === 'completed');
  const totalValue = completedCards.reduce((sum, card) => 
    sum + (card.result?.estimated_value || 0), 0
  );

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Bulk Card Scanner</h1>
          <p className="mt-2 text-gray-600">
            Upload multiple card images for batch processing with AI-powered OCR and pricing
          </p>
        </div>

        {/* Upload Zone */}
        <div className="mb-8">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragActive 
                ? 'border-blue-400 bg-blue-50' 
                : 'border-gray-300 hover:border-gray-400'
            } ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <input {...getInputProps()} />
            <div className="space-y-4">
              <div className="text-4xl">📸</div>
              <div>
                <p className="text-lg font-medium">
                  {isDragActive 
                    ? 'Drop your card images here...' 
                    : 'Drag & drop card images, or click to select'
                  }
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Supports JPEG, PNG, WebP. Upload up to 50 cards at once.
                </p>
              </div>
            </div>
          </div>

          {cards.length > 0 && (
            <div className="mt-6 flex justify-between items-center">
              <div className="flex space-x-4">
                <button
                  onClick={processAllCards}
                  disabled={isProcessing || cards.every(c => c.status !== 'pending')}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isProcessing ? 'Processing...' : 'Process All Cards'}
                </button>
                <button
                  onClick={clearAll}
                  disabled={isProcessing}
                  className="bg-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-400 disabled:opacity-50 transition-colors"
                >
                  Clear All
                </button>
              </div>
              
              {completedCards.length > 0 && (
                <div className="text-right">
                  <p className="text-sm text-gray-600">
                    {completedCards.length} cards processed
                  </p>
                  <p className="text-lg font-semibold text-green-600">
                    Total Est. Value: ${totalValue.toFixed(2)}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Cards Grid */}
        {cards.length > 0 && (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">Processing Queue ({cards.length} cards)</h2>
            </div>
            
            <div className="divide-y divide-gray-200">
              {cards.map((card) => (
                <div key={card.id} className="p-6 flex items-center space-x-4">
                  {/* Preview Image */}
                  <div className="w-16 h-16 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                    <img 
                      src={URL.createObjectURL(card.file)}
                      alt="Card preview"
                      className="w-full h-full object-cover"
                    />
                  </div>

                  {/* Card Info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{card.file.name}</p>
                    <div className="flex items-center space-x-4 mt-1">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        card.status === 'completed' 
                          ? 'bg-green-100 text-green-800'
                          : card.status === 'processing'
                          ? 'bg-blue-100 text-blue-800'
                          : card.status === 'error'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {card.status === 'completed' && '✓ '}
                        {card.status === 'processing' && '⟳ '}
                        {card.status === 'error' && '✗ '}
                        {card.status.charAt(0).toUpperCase() + card.status.slice(1)}
                      </span>
                      
                      {card.status === 'processing' && (
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${card.progress}%` }}
                          ></div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Results */}
                  <div className="flex-shrink-0 text-right">
                    {card.status === 'completed' && card.result && (
                      <div>
                        <p className="font-medium">{card.result.player_name}</p>
                        <p className="text-sm text-gray-600">{card.result.set_name} ({card.result.year})</p>
                        <p className="text-sm font-medium text-green-600">
                          ${card.result.estimated_value.toFixed(2)}
                        </p>
                      </div>
                    )}
                    
                    {card.status === 'error' && (
                      <p className="text-sm text-red-600">{card.error}</p>
                    )}
                    
                    <button
                      onClick={() => removeCard(card.id)}
                      disabled={isProcessing && card.status === 'processing'}
                      className="ml-4 text-gray-400 hover:text-red-600 disabled:opacity-50"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Premium Features Callout */}
        <div className="mt-8 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-blue-900">Unlock Advanced Features</h3>
              <p className="text-blue-700 mt-1">
                Upgrade to Pro for unlimited bulk processing, CSV export, and eBay listing automation
              </p>
            </div>
            <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
              Upgrade Now
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
} 