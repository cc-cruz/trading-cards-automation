import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import Layout from '../../../components/Layout';
import { useAuth } from '../../../contexts/AuthContext';
import dynamic from 'next/dynamic';

// Lazy load chart
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { Chart, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler, TimeScale } = require('chart.js');
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore – missing types in server env
const Line: any = dynamic(() => import('react-chartjs-2').then((m) => m.Line), { ssr: false });
if (typeof window !== 'undefined' && Chart) {
  Chart.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler, TimeScale);
}

interface Card {
  id: string;
  player_name: string | null;
  set_name: string | null;
  year: string | null;
  card_number: string | null;
  price_data?: any;
}

export default function CardDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { user } = useAuth();
  const [card, setCard] = useState<Card | null>(null);
  const [history, setHistory] = useState<{ timestamp: string; price: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id || !user) return;
    const token = localStorage.getItem('token');
    if (!token) return;

    const fetchData = async () => {
      try {
        const [cardRes, histRes] = await Promise.all([
          fetch(`/api/v1/cards/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`/api/v1/cards/${id}/history`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        if (cardRes.ok) setCard(await cardRes.json());
        if (histRes.ok) setHistory(await histRes.json());
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id, user]);

  if (loading) {
    return <Layout><div className="p-8 text-center">Loading...</div></Layout>;
  }

  if (!card) {
    return <Layout><div className="p-8 text-center text-red-600">Card not found.</div></Layout>;
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">{card.player_name} {card.year} {card.set_name}</h1>
        <p className="text-gray-600 mb-6">Card Number: {card.card_number || 'N/A'}</p>

        {/* Price history */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Price History</h3>
          {history.length > 1 ? (
            <Line
              data={{
                labels: history.map((h) => new Date(h.timestamp).toLocaleDateString()),
                datasets: [{
                  label: 'Price ($)',
                  data: history.map((h) => h.price),
                  fill: true,
                  backgroundColor: 'rgba(16,185,129,0.15)',
                  borderColor: 'rgba(16,185,129,1)',
                  tension: 0.3,
                }],
              }}
              options={{
                responsive: true,
                plugins: { legend: { display: false } },
                maintainAspectRatio: false,
              }}
              height={300}
            />
          ) : (
            <p className="text-gray-500">No price history yet.</p>
          )}
        </div>
      </div>
    </Layout>
  );
} 