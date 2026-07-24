import { memo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ChartSeries } from '@/types/hospital';

const COLORS = [
  '#0284c7',
  '#059669',
  '#d97706',
  '#7c3aed',
  '#e11d48',
  '#0891b2',
  '#4f46e5',
  '#65a30d',
];

interface SimpleChartProps {
  title: string;
  data: ChartSeries[];
  type?: 'bar' | 'line' | 'pie';
}

function SimpleChart({ title, data, type = 'bar' }: SimpleChartProps) {
  const chartData = data.map((d) => ({ name: d.label, value: d.value }));

  return (
    <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
      <h3 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
        {title}
      </h3>
      <div className="h-56 w-full">
        {!chartData.length ? (
          <p className="flex h-full items-center justify-center text-sm text-[var(--text-secondary)]">
            No data yet
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {type === 'line' ? (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#0284c7"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            ) : type === 'pie' ? (
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name }) => name}
                >
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            ) : (
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#0284c7" radius={[4, 4, 0, 0]} />
              </BarChart>
            )}
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

export default memo(SimpleChart);
