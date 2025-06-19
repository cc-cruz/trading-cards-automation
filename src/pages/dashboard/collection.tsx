import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import Layout from '../../components/Layout';

interface Card {
  id: string;
  player_name: string;
  set_name: string;
  year: string;
  card_number: string;
  price_data?: {
    estimated_value: number;
    listing_price: number;
  };
}

interface Collection {
  id: string;
  name: string;
  description: string;
  cards: Card[];
}

export default function Collection() {
  const { user } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [showExportModal, setShowExportModal] = useState(false);

  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    try {
      const response = await fetch('/api/v1/collections', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setCollections(data);
        if (data.length > 0) {
          setSelectedCollection(data[0]);
        }
      }
    } catch (error) {
      console.error('Error fetching collections:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = async () => {
    if (!selectedCollection) return;
    
    try {
      const response = await fetch(`/api/v1/collections/${selectedCollection.id}/export`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ format: 'csv' }),
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedCollection.name}_cards.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Error exporting collection. Please try again.');
    }
  };

  const createEbayListings = async () => {
    if (!selectedCollection) return;
    
    try {
      const response = await fetch(`/api/v1/collections/${selectedCollection.id}/create-listings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`Success! Ready to create ${result.total_cards} eBay listings worth $${result.total_listing_value.toFixed(2)}`);
      } else {
        throw new Error('Failed to create listings');
      }
    } catch (error) {
      console.error('Error creating eBay listings:', error);
      alert('Error creating eBay listings. Please try again.');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">My Collections</h1>
          <p className="mt-2 text-gray-600">
            Manage your trading card collections and export for eBay listings
          </p>
        </div>

        {collections.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg">
              <p>No collections found</p>
              <p className="mt-2">Start by uploading some cards!</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Collections Sidebar */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4">Collections</h2>
                <div className="space-y-2">
                  {collections.map((collection) => (
                    <button
                      key={collection.id}
                      onClick={() => setSelectedCollection(collection)}
                      className={`w-full text-left p-3 rounded-lg transition-colors ${
                        selectedCollection?.id === collection.id
                          ? 'bg-blue-50 border-blue-200 border'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="font-medium">{collection.name}</div>
                      <div className="text-sm text-gray-500">
                        {collection.cards?.length || 0} cards
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Collection Details */}
            <div className="lg:col-span-3">
              {selectedCollection && (
                <div className="bg-white rounded-lg shadow">
                  {/* Header */}
                  <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex justify-between items-start">
                      <div>
                        <h2 className="text-xl font-semibold">{selectedCollection.name}</h2>
                        <p className="text-gray-600 mt-1">{selectedCollection.description}</p>
                      </div>
                      <div className="flex space-x-3">
                        <button
                          onClick={() => setShowExportModal(true)}
                          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                        >
                          Export CSV
                        </button>
                        <button 
                          onClick={createEbayListings}
                          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          Create eBay Listings
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Cards Grid */}
                  <div className="p-6">
                    {selectedCollection.cards && selectedCollection.cards.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {selectedCollection.cards.map((card) => (
                          <div key={card.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                            <h3 className="font-semibold">{card.player_name}</h3>
                            <p className="text-sm text-gray-600">{card.set_name} ({card.year})</p>
                            {card.card_number && (
                              <p className="text-sm text-gray-500">#{card.card_number}</p>
                            )}
                            {card.price_data && (
                              <p className="text-sm font-medium text-green-600 mt-2">
                                Est. Value: ${card.price_data.estimated_value?.toFixed(2)}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center text-gray-500 py-8">
                        No cards in this collection
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Export Modal */}
        {showExportModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <h3 className="text-lg font-semibold mb-4">Export Collection</h3>
              <p className="text-gray-600 mb-6">
                Export your collection as a CSV file ready for eBay bulk upload.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => {
                    exportToCSV();
                    setShowExportModal(false);
                  }}
                  className="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors"
                >
                  Export CSV
                </button>
                <button
                  onClick={() => setShowExportModal(false)}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-400 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
} 