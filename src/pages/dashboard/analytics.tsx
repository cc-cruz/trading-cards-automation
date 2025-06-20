import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import Layout from '../../components/Layout';
import dynamic from 'next/dynamic';

interface AnalyticsData {
  total_cards: number;
  total_value: number;
  recent_additions: number;
  collections: CollectionStats[];
  value_trends: ValueTrend[];
  top_cards: TopCard[];
}

interface CollectionStats {
  id: string;
  name: string;
  card_count: number;
  total_value: number;
  avg_value: number;
}

interface ValueTrend {
  date: string;
  total_value: number;
}

interface TopCard {
  id: string;
  name: string;
  set: string;
  condition: string;
  value: number;
  image_url: string;
}

// @ts-ignore - using require for runtime import to avoid SSR issues
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { Chart, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler, TimeScale } = require('chart.js');

// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore – react-chartjs-2 types installed at runtime
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Line: any = dynamic(() => import('react-chartjs-2').then((mod) => mod.Line), { ssr: false });

// Register chart components if in browser
if (typeof window !== 'undefined' && Chart) {
  Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler, TimeScale);
}

export default function Analytics() {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      fetchAnalytics();
    }
  }, [user]);

  const fetchAnalytics = async () => {
    try {
      const response = await fetch('/api/v1/analytics', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }

      const data = await response.json();
      setAnalytics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
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

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-medium">Error Loading Analytics</h3>
          <p className="text-red-600 mt-2">
            {typeof error === 'string' ? error : 'An error occurred while loading analytics.'}
          </p>
        </div>
      </Layout>
    );
  }

  if (!analytics) {
    return (
      <Layout>
        <div className="text-center py-8">
          <h3 className="text-gray-500 text-lg">No analytics data available</h3>
          <p className="text-gray-400 mt-2">Upload some cards to see your collection analytics</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Collection Analytics</h1>
          <p className="text-gray-600 mt-2">Deep insights into your trading card collection</p>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 012-2h10a2 2 0 012 2v2M7 7V6a2 2 0 012-2h6a2 2 0 012 2v1" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Cards</p>
                <p className="text-2xl font-bold text-gray-900">{analytics.total_cards}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Value</p>
                <p className="text-2xl font-bold text-gray-900">${analytics.total_value.toFixed(2)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Recent Additions</p>
                <p className="text-2xl font-bold text-gray-900">{analytics.recent_additions}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Collections Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Collections Breakdown</h3>
            <div className="space-y-4">
              {analytics.collections.map((collection) => (
                <div key={collection.id} className="flex justify-between items-center">
                  <div>
                    <p className="font-medium text-gray-900">{collection.name}</p>
                    <p className="text-sm text-gray-500">{collection.card_count} cards</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-gray-900">${collection.total_value.toFixed(2)}</p>
                    <p className="text-sm text-gray-500">avg: ${collection.avg_value.toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Valuable Cards</h3>
            <div className="space-y-4">
              {analytics.top_cards.map((card) => (
                <div key={card.id} className="flex items-center space-x-4">
                  <img
                    src={card.image_url}
                    alt={card.name}
                    className="w-12 h-16 object-cover rounded"
                    onError={(e) => {
                      e.currentTarget.src = '/images/card-placeholder.jpg';
                    }}
                  />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{card.name}</p>
                    <p className="text-sm text-gray-500">{card.set} • {card.condition}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-gray-900">${card.value.toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Value Trends Line Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Collection Value Trends (Last 90 Days)</h3>
          {analytics.value_trends && analytics.value_trends.length > 1 ? (
            <Line
              data={{
                labels: analytics.value_trends.map((v) => v.date),
                datasets: [
                  {
                    label: 'Total Value ($)',
                    data: analytics.value_trends.map((v) => v.total_value),
                    fill: true,
                    backgroundColor: 'rgba(59,130,246,0.15)',
                    borderColor: 'rgba(59,130,246,1)',
                    tension: 0.3,
                  },
                ],
              }}
              options={{
                responsive: true,
                plugins: {
                  legend: {
                    display: false,
                  },
                  tooltip: {
                    callbacks: {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      label: (ctx: any) => `$${ctx.parsed.y.toFixed(2)}`,
                    },
                  },
                },
                scales: {
                  x: {
                    display: true,
                    title: {
                      display: false,
                    },
                  },
                  y: {
                    display: true,
                    title: {
                      display: false,
                    },
                  },
                },
                maintainAspectRatio: false,
              }}
              height={320}
            />
          ) : (
            <p className="text-gray-500 text-center">No price history yet.</p>
          )}
        </div>
      </div>
    </Layout>
  );
} 