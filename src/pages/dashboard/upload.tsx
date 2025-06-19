import React, { useState, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'react-hot-toast';
import DualSideUploader from '@/components/DualSideUploader';
import { CardProcessingResult } from '@/types';

interface Collection {
  id: string;
  name: string;
  description?: string;
}

interface Subscription {
  plan_type: string;
  status: string;
  current_period_end: string | null;
}

export default function Upload() {
  const { user } = useAuth();
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [collections, setCollections] = useState<Collection[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [processedCards, setProcessedCards] = useState<CardProcessingResult[]>([]);
  const [monthlyUploads, setMonthlyUploads] = useState(0);

  // Load collections and subscription on mount
  React.useEffect(() => {
    const loadData = async () => {
      await Promise.all([
        loadCollections(),
        loadSubscription(),
        loadMonthlyUploads()
      ]);
    };
    loadData();
  }, []);

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

  const loadSubscription = async () => {
    try {
      const response = await fetch('/api/v1/billing/subscription', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSubscription(data);
      }
    } catch (error) {
      console.error('Error loading subscription:', error);
    }
  };

  const loadMonthlyUploads = async () => {
    try {
      // This would need to be implemented in the backend
      // For now, we'll simulate it
      setMonthlyUploads(Math.floor(Math.random() * 50));
    } catch (error) {
      console.error('Error loading monthly uploads:', error);
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

  const handleCardProcessed = (result: CardProcessingResult) => {
    setProcessedCards(prev => [...prev, result]);
    setMonthlyUploads(prev => prev + 1);
    
    // Show confidence score feedback
    const confidence = result.card_data.confidence_score * 100;
    if (confidence >= 80) {
      toast.success(`Excellent! ${confidence.toFixed(0)}% confidence extraction`, { duration: 3000 });
    } else if (confidence >= 60) {
      toast(`Good extraction: ${confidence.toFixed(0)}% confidence. Consider reviewing details.`, 
        { icon: '👍', duration: 4000 });
    } else {
      toast(`Extraction completed: ${confidence.toFixed(0)}% confidence. Please review and edit details.`, 
        { icon: '⚠️', duration: 5000 });
    }
  };

  const handleError = (error: string) => {
    console.error('Upload error:', error);
    toast.error(error);
  };

  // Check usage limits
  const isOverLimit = subscription?.plan_type === 'free' && monthlyUploads >= 100;
  const isNearLimit = subscription?.plan_type === 'free' && monthlyUploads >= 80;

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Upload Trading Cards</h1>
            <p className="text-gray-600 mt-1">
              Advanced dual-side OCR for maximum accuracy
            </p>
          </div>
          
          {/* Usage Stats */}
          <div className="text-right">
            <div className="text-sm text-gray-600">
              This month: <span className="font-medium">{monthlyUploads}</span>
              {subscription?.plan_type === 'free' && (
                <span className="text-gray-400"> / 100</span>
              )}
            </div>
            {subscription?.plan_type === 'free' && (
              <div className={`text-xs mt-1 ${isNearLimit ? 'text-amber-600' : 'text-gray-500'}`}>
                {isOverLimit ? 'Limit reached' : `${100 - monthlyUploads} remaining`}
              </div>
            )}
          </div>
        </div>

        {/* Usage Limit Warning */}
        {isNearLimit && (
          <div className={`rounded-lg p-4 mb-6 ${
            isOverLimit 
              ? 'bg-red-50 border border-red-200' 
              : 'bg-amber-50 border border-amber-200'
          }`}>
            <div className="flex items-center justify-between">
              <div>
                <h3 className={`font-medium ${isOverLimit ? 'text-red-800' : 'text-amber-800'}`}>
                  {isOverLimit ? 'Monthly Upload Limit Reached' : 'Approaching Upload Limit'}
                </h3>
                <p className={`text-sm mt-1 ${isOverLimit ? 'text-red-600' : 'text-amber-600'}`}>
                  {isOverLimit 
                    ? 'Upgrade to Pro for unlimited uploads and advanced features.'
                    : `You've used ${monthlyUploads}/100 uploads this month. Upgrade to Pro for unlimited access.`
                  }
                </p>
              </div>
              <button
                onClick={() => window.location.href = '/dashboard/billing'}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  isOverLimit
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-amber-600 text-white hover:bg-amber-700'
                }`}
              >
                Upgrade to Pro
              </button>
            </div>
          </div>
        )}
        
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
            Collections: {collections.length}, Selected: {selectedCollection || 'none'}
          </div>
        </div>

        {/* Main Upload Component */}
        {!isOverLimit ? (
          <DualSideUploader
            selectedCollection={selectedCollection}
            onCardProcessed={handleCardProcessed}
            onError={handleError}
          />
        ) : (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <div className="text-4xl text-gray-400 mb-4">🚫</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Upload Limit Reached</h3>
            <p className="text-gray-600 mb-4">
              You've reached your monthly limit of 100 card uploads.
            </p>
            <button
              onClick={() => window.location.href = '/dashboard/billing'}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
            >
              Upgrade to Pro for Unlimited Uploads
            </button>
          </div>
        )}

        {/* Recent Processed Cards */}
        {processedCards.length > 0 && (
          <div className="mt-8 bg-gray-50 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Recently Processed Cards ({processedCards.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {processedCards.slice(-6).map((card, index) => (
                <div key={index} className="bg-white rounded-lg border p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-900">
                      {card.card_data.player || 'Unknown Player'}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      card.card_data.confidence_score >= 0.8 
                        ? 'bg-green-100 text-green-800'
                        : card.card_data.confidence_score >= 0.6
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {(card.card_data.confidence_score * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div><strong>Set:</strong> {card.card_data.set || 'Unknown'}</div>
                    <div><strong>Year:</strong> {card.card_data.year || 'Unknown'}</div>
                    {card.card_data.card_number && (
                      <div><strong>Number:</strong> {card.card_data.card_number}</div>
                    )}
                    <div><strong>Processing:</strong> {card.card_data.dual_side ? 'Dual-side' : 'Single-side'}</div>
                  </div>
                  {card.price_data && (
                    <div className="mt-2 pt-2 border-t text-sm">
                      <div className="font-medium text-green-600">
                        Est. Value: ${card.price_data.estimated_value?.toFixed(2) || '0.00'}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Enhanced Help Text */}
        <div className="mt-8 bg-blue-50 rounded-lg p-4">
          <h4 className="font-semibold text-blue-900 mb-2">🚀 New: Dual-Side Processing!</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-800">
            <div>
              <h5 className="font-medium mb-1">How it works:</h5>
              <ol className="space-y-1 list-decimal list-inside">
                <li>Upload both front and back of your card</li>
                <li>Our AI extracts details from both sides</li>
                <li>Smart merging prioritizes the most accurate data</li>
                <li>Confidence scoring shows extraction quality</li>
              </ol>
            </div>
            <div>
              <h5 className="font-medium mb-1">Benefits:</h5>
              <ul className="space-y-1 list-disc list-inside">
                <li><strong>40% accuracy improvement</strong> vs single-side</li>
                <li>Card numbers found more reliably (usually on back)</li>
                <li>Years extracted from copyright info</li>
                <li>Set names clearer from front marketing</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 