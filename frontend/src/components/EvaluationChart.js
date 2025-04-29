// Last reviewed: 2025-04-29 06:57:37 UTC (User: Teeksss)
import React, { useEffect, useRef } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const EvaluationChart = ({ evaluationResults }) => {
    const chartRef = useRef(null);
    useEffect(() => { const chart = chartRef.current; return () => { if (chart) chart.destroy(); }; }, []);

    if (!evaluationResults || Object.keys(evaluationResults).length === 0) {
        return <div className="evaluation-chart-container"><p>Değerlendirme sonuçları bekleniyor...</p></div>;
    }

    const labels = Object.keys(evaluationResults).map(key => key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
    const dataValues = Object.values(evaluationResults);

    const data = {
        labels,
        datasets: [{
            label: 'Metrik Skoru', data: dataValues,
            backgroundColor: 'rgba(54, 162, 235, 0.6)', borderColor: 'rgba(54, 162, 235, 1)', borderWidth: 1,
        }],
    };
    const options = {
        responsive: true, maintainAspectRatio: false, indexAxis: 'y', // Yatay bar grafik
        plugins: {
            legend: { display: false },
            title: { display: true, text: 'RAG Değerlendirme Metrikleri', font: { size: 16 } },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label || ''}: ${ctx.parsed.x !== null ? ctx.parsed.x.toFixed(3) : 'N/A'}` } }
        },
        scales: {
            x: { beginAtZero: true, suggestedMax: 1, title: { display: true, text: 'Skor' } },
            y: { ticks: { autoSkip: false } }
        },
    };

    return (
        // Dinamik yükseklik: Etiket sayısına göre ayarla, minimum yükseklik belirle
        <div className="evaluation-chart-container" style={{ height: `${Math.max(200, labels.length * 35 + 60)}px`, border: 'none', padding: 0 }}>
            <Bar ref={chartRef} options={options} data={data} />
        </div>
    );
};

export default EvaluationChart;