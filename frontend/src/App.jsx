import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  TrendingUp, Users, Briefcase, FileText, CreditCard, X, Download, ChevronRight, Search, ArrowLeft, Calendar, Layers
} from 'lucide-react';

// --- Theme Synced with index.css ---
const COLORS = {
  purple: '#6366f1',      // Indigo-500 (Primary)
  purpleDark: '#4f46e5',   // Indigo-600
  purpleLight: '#818cf8',  // Indigo-400
  blue: '#3b82f6',        // Blue-500
  blueDark: '#2563eb',     // Blue-600
  slate: '#475569',       // Slate-600
  border: '#cbd5e1',      // Desaturated slate border
  cardBg: '#ffffff',
  textMuted: '#64748b',
  textDim: '#94a3b8',
  textMain: '#1e293b',
  green: '#10b981',       // Emerald-500 (Success)
  red: '#ef4444',         // Red-500 (Alert)
};

const theme = {
  color: [COLORS.purple, COLORS.blue, COLORS.pink, COLORS.teal, COLORS.yellow],
  backgroundColor: 'transparent',
  textStyle: { color: COLORS.textMuted, fontFamily: 'Inter, sans-serif' },
  title: { textStyle: { color: COLORS.textMain, fontWeight: '700' } },
  line: { smooth: false, width: 2 },
  categoryAxis: {
    axisLine: { lineStyle: { color: COLORS.border } },
    axisTick: { show: false },
    splitLine: { show: false }
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: COLORS.border, type: 'dashed', opacity: 0.3 } }
  },
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.98)',
    borderColor: COLORS.border,
    textStyle: { color: COLORS.textMain },
    extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-radius: 8px;'
  }
};

// --- Helper Components ---

const KPICard = ({ label, value, trend, color = COLORS.purple }) => {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value-row">
        <div className="kpi-value">{value}</div>
        <div className="kpi-trend" style={{ color: trend.includes('+') ? COLORS.green : COLORS.red }}>{trend}</div>
      </div>
    </div>
  );
};

const InsightCapsule = ({ content }) => (
  <div className="insight-capsule">
    <div className="insight-label">Chumley Insights</div>
    <div className="insight-content">{content}</div>
  </div>
);

const BigInsight = ({ content }) => (
  <div style={{
    marginTop: '12px',
    padding: '20px 24px',
    background: 'rgba(255, 255, 255, 0.6)',
    backdropFilter: 'blur(8px)',
    border: `1px solid ${COLORS.border}`,
    borderRadius: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)'
  }}>
    <div style={{
      background: COLORS.purple,
      borderRadius: '12px',
      padding: '12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <TrendingUp size={24} color="#fff" />
    </div>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: '11px', color: COLORS.purple, fontWeight: '900', textTransform: 'uppercase', marginBottom: '4px', letterSpacing: '0.08em' }}>Review Information</div>
      <div style={{ fontSize: '15px', fontWeight: '700', color: COLORS.textMain, lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>{content}</div>
    </div>
  </div>
);

// --- Chart Option Generators ---

const getSalesOption = ({ salesView, data }) => ({
  tooltip: { 
    trigger: 'axis',
    formatter: (p) => {
      const d = p[0];
      const val = d.value > 1000000 ? `£${(d.value / 1000000).toFixed(2)}M` : `£${Math.round(d.value / 1000)}k`;
      return `${d.name}<br/>${d.marker} ${d.seriesName}: <b>${val}</b>`;
    }
  },
  grid: { left: '3%', right: '4%', bottom: '5%', top: '15%', containLabel: true },
  xAxis: {
    type: 'category',
    data: data.sales[salesView].map(d => d.date),
    axisLabel: { color: COLORS.textMain, fontSize: 11, fontWeight: 'bold' },
    boundaryGap: false
  },
  yAxis: {
    type: 'value',
    axisLabel: { formatter: v => `£${(v / 1000000).toFixed(2)}M`, color: COLORS.textMain, fontWeight: 'bold' },
  },
  series: [
    {
      name: 'Actual Sales',
      data: data.sales[salesView].map(d => d.sales),
      type: 'line',
      symbol: 'circle',
      symbolSize: 6,
      label: {
        show: true,
        position: 'top',
        formatter: (p) => `£${(p.value / 1000000).toFixed(0)}M`,
        color: COLORS.textMain,
        fontWeight: '900',
        fontSize: 11
      },
      areaStyle: {
        color: 'rgba(139, 92, 246, 0.15)'
      }
    }
  ]
});

const getCollectionsTrendOption = ({ data }) => ({
  tooltip: { 
    trigger: 'axis',
    formatter: (p) => {
      const d = p[0];
      const val = d.value > 1000000 ? `£${(d.value / 1000000).toFixed(2)}M` : `£${Math.round(d.value / 1000)}k`;
      return `${d.name}<br/>${d.marker} Collections: <b>${val}</b>`;
    }
  },
  grid: { left: '3%', right: '4%', bottom: '5%', top: '15%', containLabel: true },
  xAxis: {
    type: 'category',
    data: data.coll?.history?.map(d => d.month) || [],
    axisLabel: { color: COLORS.textMain, fontSize: 11, fontWeight: 'bold' }
  },
  yAxis: {
    type: 'value',
    axisLabel: { formatter: v => `£${(v / 1000000).toFixed(2)}M`, color: COLORS.textMain, fontWeight: 'bold' },
  },
  series: [{
    data: data.coll?.history?.map(d => d.value) || [],
    type: 'line',
    smooth: false,
    itemStyle: { color: COLORS.purpleLight },
    lineStyle: { width: 3 },
    symbolSize: 6,
    label: {
      show: true,
      position: 'top',
      formatter: (p) => `£${(p.value / 1000000).toFixed(0)}M`,
      fontSize: 10,
      color: COLORS.textMain,
      fontWeight: 'bold'
    },
    areaStyle: {
      color: 'rgba(129, 140, 248, 0.1)'
    }
  }]
});

const getCollectionsProgressOption = ({ data }) => {
  const current = data.coll?.total || 0;
  const target = data.sum?.net_sales_raw || 1;
  const percentage = Math.min((current / target) * 100, 100);

  return {
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        center: ['50%', '75%'],
        radius: '140%',
        pointer: {
          show: true,
          length: '65%',
          width: 5,
          itemStyle: { color: COLORS.purple }
        },
        progress: {
          show: true,
          roundCap: true,
          width: 14,
          itemStyle: { color: COLORS.purple }
        },
        axisLine: { lineStyle: { width: 14, color: [[1, '#f1f5f9']] } },
        splitLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        data: [{ value: Math.round(percentage) }],
        detail: {
          offsetCenter: [0, '-50%'],
          fontWeight: '900',
          fontSize: 20,
          color: COLORS.textMain,
          formatter: '{value}%'
        }
      }
    ]
  };
};

const getAgingOption = ({ data }) => {
  const buckets = data.out?.aging?.by_type || {};
  const categories = ['Cash', 'Credit', 'Key Account'];
  const values = categories.map(cat => buckets[cat] || 0);

  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (p) => {
        const d = p[0];
        return `${d.name}<br/>${d.marker} ${d.seriesName}: <b>£${Math.round(d.value / 1000)}k</b>`;
      }
    },
    grid: { left: '15%', right: '15%', bottom: '10%', top: '5%', containLabel: true },
    xAxis: { type: 'value', show: false },
    yAxis: {
      type: 'category',
      data: categories,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: COLORS.textMain, fontWeight: 'bold' }
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: COLORS.purpleLight,
        borderRadius: 0
      },
      barWidth: '50%',
      label: { show: true, position: 'right', formatter: p => `£${(p.value / 1000).toFixed(0)}k`, fontWeight: '900', fontSize: 11, color: COLORS.textMain }
    }]
  };
};

const getAJVOption = ({ data }) => {
  const ajvData = data.out?.ajv || [];
  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (p) => {
        const d = p[0];
        return `${d.name}<br/>${d.marker} AJV: <b>£${Math.round(d.value)}</b>`;
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ajvData.map(d => d.month), axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
    yAxis: { type: 'value', axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
    series: [{
      data: ajvData.map(d => d.value),
      type: 'line',
      smooth: false,
      itemStyle: { color: COLORS.blue },
      lineStyle: { width: 3 },
      symbolSize: 6,
      label: { show: true, position: 'top', formatter: p => `£${Math.round(p.value)}`, fontSize: 11, fontWeight: 'bold', color: COLORS.textMain }
    }]
  };
};

const getByTradeOption = ({ data, drilldownTrade, selectedJobType }) => {
  let rawData = [];
  if (selectedJobType && data.sas.type_trade_split) {
    const split = data.sas.type_trade_split[selectedJobType] || {};
    rawData = Object.entries(split).map(([name, value]) => ({ name, value }));
  } else if (drilldownTrade) {
    const parentGroup = data.sas.by_trade?.find(t => t.name === drilldownTrade);
    rawData = parentGroup ? parentGroup.sub_trades : [];
  } else {
    rawData = (data.sas.by_trade || []).slice(0, 10);
  }

  let sortedTrades = [...rawData].sort((a, b) => a.value - b.value);
  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (p) => {
        const d = p[0];
        return `${d.name}<br/>${d.marker} Value: <b>£${Math.round(d.value / 1000)}k</b>`;
      }
    },
    grid: { left: '3%', right: '15%', bottom: '3%', top: '3%', containLabel: true },
    xAxis: { type: 'value', show: false },
    yAxis: {
      type: 'category',
      data: sortedTrades.map(t => t.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: COLORS.textMain, fontWeight: 'bold' }
    },
    series: [{
      type: 'bar',
      data: sortedTrades.map(t => ({
        value: t.value,
        itemStyle: {
          color: '#8B5CF6',
          borderRadius: 0
        }
      })),
      label: { show: true, position: 'right', formatter: p => `£${(p.value / 1000).toFixed(0)}k`, color: COLORS.textMain, fontWeight: 'bold' }
    }]
  };
};

const getJobTypeOption = ({ data, donutDrill }) => {
  let fmtData = [];
  if (donutDrill && data.sas.type_trade_split) {
    const split = data.sas.type_trade_split[donutDrill] || {};
    fmtData = Object.entries(split).map(([name, value]) => ({ name, value }));
  } else {
    fmtData = data.sas.sa_job_types || [];
  }

  const total = fmtData.reduce((a, b) => a + b.value, 0);

  return {
    tooltip: { 
      trigger: 'item',
      formatter: (p) => {
        const val = p.value;
        const formatted = val > 1000 ? `£${Math.round(val / 1000)}k` : Math.round(val);
        return `${p.marker} ${p.name}: <b>${formatted}</b> (${Math.round(p.percent)}%)`;
      }
    },
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: `TOTAL\n${donutDrill ? '£' + (total / 1000).toFixed(0) + 'k' : total}`,
        textAlign: 'center',
        fill: COLORS.textMain,
        fontSize: 14,
        fontWeight: '900'
      }
    }],
    series: [{
      type: 'pie',
      radius: ['60%', '85%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 0, borderColor: '#fff', borderWidth: 2 },
      label: {
        show: true,
        position: 'outside',
        formatter: (params) => {
          if (!donutDrill) return `${params.name}: ${Math.round(params.value)}`;
          return `${params.name}: £${Math.round(params.value / 1000)}k`;
        },
        color: COLORS.textMain,
        fontWeight: '900',
        fontSize: 12
      },
      labelLine: {
        show: true,
        length: 20,
        length2: 15,
        lineStyle: { color: COLORS.border, width: 2 }
      },
      data: fmtData.map((d, i) => ({
        ...d,
        itemStyle: { color: [COLORS.purple, COLORS.blue, COLORS.pink, COLORS.teal][i % 4] }
      }))
    }]
  };
};

const getSASummaryOption = ({ summaryData }) => {
  const new_cust = summaryData.new || 0;
  const existing_cust = summaryData.existing || 0;

  return {
    tooltip: { 
      trigger: 'item',
      formatter: (p) => `${p.marker} ${p.name}: <b>${Math.round(p.value)}</b> (${Math.round(p.percent)}%)`
    },
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: `TOTAL\n${summaryData.total || 0}`,
        textAlign: 'center',
        fill: COLORS.textMain,
        fontSize: 14,
        fontWeight: '900'
      }
    }],
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 0,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        position: 'outside',
        formatter: (params) => `${params.name}: ${Math.round(params.value)}`,
        color: COLORS.textMain,
        fontWeight: 'bold',
        fontSize: 12
      },
      labelLine: {
        show: true,
        length: 15,
        length2: 10,
        lineStyle: { color: COLORS.border }
      },
      data: [
        {
          name: 'New',
          value: new_cust,
          itemStyle: {
            color: '#8B5CF6'
          }
        },
        {
          name: 'Existing',
          value: existing_cust,
          itemStyle: {
            color: '#3b82f6'
          }
        }
      ],
    }]
  };
};

const getSATradesOption = ({ data }) => {
  const trades = data.sas.summary.month.trades || [];
  const sorted = [...trades].sort((a, b) => b.value - a.value).slice(0, 10);

  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (p) => {
        const d = p[0];
        return `${d.name}<br/>${d.marker} SAs: <b>${Math.round(d.value)}</b>`;
      }
    },
    grid: { left: '3%', right: '15%', bottom: '5%', top: '5%', containLabel: true },
    xAxis: { type: 'value', show: false },
    yAxis: {
      type: 'category',
      data: sorted.map(d => d.name),
      inverse: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: COLORS.textMain, fontWeight: '900', fontSize: 12 }
    },
    series: [{
      type: 'bar',
      data: sorted.map(d => ({
        value: d.value,
        itemStyle: {
          color: '#8B5CF6',
          borderRadius: 0
        }
      })),
      label: { show: true, position: 'right', formatter: p => Math.round(p.value), fontWeight: '900', fontSize: 12, color: COLORS.textMain }
    }]
  };
};

const getJobTypeSalesOption = ({ data }) => {
  const srcData = data.sas.month_split || [];
  const reactive = srcData.find(d => d.name === 'Reactive') || { sales: 0 };
  const fixed = srcData.find(d => d.name === 'Fixed Price') || { sales: 0 };

  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (p) => {
        return `${p[0].name}<br/>` + p.map(d => `${d.marker} ${d.seriesName}: <b>£${Math.round(d.value / 1000)}k</b>`).join('<br/>');
      }
    },
    grid: { left: '3%', right: '5%', bottom: '20%', top: '20%', containLabel: true },
    xAxis: { type: 'value', show: false },
    yAxis: { type: 'category', data: ['Sales'], show: false },
    series: [
      {
        name: 'Reactive',
        type: 'bar',
        stack: 'total',
        data: [{
          value: reactive.sales,
          itemStyle: {
            color: '#3b82f6',
            borderRadius: 0
          }
        }],
        label: { show: true, formatter: (p) => `Reactive: £${Math.round(p.value / 1000)}k`, color: '#fff', fontWeight: 'bold', fontSize: 12 }
      },
      {
        name: 'Fixed Price',
        type: 'bar',
        stack: 'total',
        data: [{
          value: fixed.sales,
          itemStyle: {
            color: '#8B5CF6',
            borderRadius: 0
          }
        }],
        label: { show: true, formatter: (p) => `Fixed: £${Math.round(p.value / 1000)}k`, color: '#fff', fontWeight: 'bold', fontSize: 12 }
      }
    ]
  };
};

// --- Main Application ---

const App = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [tradeFilter, setTradeFilter] = useState('');
  const [salesView, setSalesView] = useState('monthly');
  const [drilldownTrade, setDrilldownTrade] = useState(null);
  const [donutDrill, setDonutDrill] = useState(null);
  const [insights, setInsights] = useState({});

  useEffect(() => {
    const API_BASE = 'http://localhost:8000/api';
    const fetchAll = async () => {
      try {
        const [sum, sales, jobs, coll, out, sas, insightRes] = await Promise.all([
          fetch(`${API_BASE}/stats/summary`).then(r => r.json()),
          fetch(`${API_BASE}/stats/sales`).then(r => r.json()),
          fetch(`${API_BASE}/stats/jobs`).then(r => r.json()),
          fetch(`${API_BASE}/stats/collections`).then(r => r.json()),
          fetch(`${API_BASE}/stats/outstanding`).then(r => r.json()),
          fetch(`${API_BASE}/stats/sas`).then(r => r.json()),
          fetch(`${API_BASE}/stats/insights`).then(r => r.json())
        ]);
        setData({ sum, sales, jobs, coll, out, sas });
        setInsights(insightRes);
        setLoading(false);
      } catch (e) { console.error(e); }
    };
    fetchAll();
  }, []);

  if (loading) return <div style={{ background: '#f8f7ff', height: '100vh', padding: '40px', color: '#1e293b' }}>Initializing Aspect Dashboard...</div>;

  return (
    <div className="dashboard-wrapper">
      <main className="main-viewport" style={{ paddingBottom: '60px' }}>
        <header className="dashboard-header">
          <img src="/Aspect_Logo.svg" alt="Aspect Logo" style={{ height: '28px' }} />
          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              background: 'rgba(255, 255, 255, 0.5)',
              border: `1px solid ${COLORS.border}`,
              borderRadius: '10px',
              fontSize: '12px',
              color: COLORS.textMain,
              fontWeight: '600'
            }}>
              <Calendar size={14} /> Date Range: <span style={{ color: COLORS.purple }}>Last 30 Days</span>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              background: 'rgba(255, 255, 255, 0.5)',
              border: `1px solid ${COLORS.border}`,
              borderRadius: '10px',
              fontSize: '12px',
              color: COLORS.textMain,
              fontWeight: '600'
            }}>
              <Layers size={14} /> Sector: <span style={{ color: COLORS.purple }}>All Sectors</span>
            </div>
            <button style={{
              background: COLORS.textMain,
              border: 'none',
              color: '#fff',
              padding: '6px 16px',
              borderRadius: '10px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontWeight: '600'
            }}>
              <Download size={14} /> Export
            </button>
          </div>
        </header>

        <div className="kpi-grid">
          <KPICard label="Total Invoices " value={data.sum.invoice_count.value} trend={data.sum.invoice_count.trend} color={COLORS.blue} />
          <KPICard label="Net Sales" value={data.sum.net_sales.value} trend={data.sum.net_sales.trend} color={COLORS.purple} />
          <KPICard label="Outstanding" value={data.sum.outstanding_amount.value} trend={data.sum.outstanding_amount.trend} color={COLORS.pink} />
        </div>

        <div className="view-container">
          <section className="dashboard-section">
            <h2 className="section-title-main"><TrendingUp size={32} /> Sales & Collections Performance</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '7fr 3fr', gap: '12px' }}>
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title"></div>
                  <div className="toggle-group">
                    <button className={`toggle-btn ${salesView === 'monthly' ? 'active' : ''}`} onClick={() => setSalesView('monthly')}>Monthly</button>
                    <button className={`toggle-btn ${salesView === 'quarterly' ? 'active' : ''}`} onClick={() => setSalesView('quarterly')}>Quarterly</button>
                  </div>
                </div>
                <ReactECharts option={getSalesOption({ salesView, data })} theme={theme} onEvents={{ 'click': (p) => { setSelectedPoint(p); setSidePanelOpen(true); } }} style={{ height: '350px' }} />
                <InsightCapsule content={insights.sales} />
              </div>
              <div className="chart-card" style={{ display: 'flex', flexDirection: 'column' }}>
                <div className="card-header">
                  <div className="card-title" style={{ fontSize: '13px', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Collections MTD</div>
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '10px' }}>
                  <ReactECharts option={getCollectionsProgressOption({ data })} theme={theme} style={{ height: '140px', width: '100%' }} />
                  <div style={{ textAlign: 'center', marginTop: '10px' }}>
                    <div style={{ fontSize: '24px', fontWeight: '900', color: COLORS.textMain }}>{data.coll?.total ? `£${(data.coll.total / 1000).toFixed(0)}k` : '£0k'}</div>
                    <div style={{ fontSize: '12px', color: COLORS.textMuted }}>Current Revenue: <span style={{ fontWeight: '700' }}>{data.sum?.net_sales?.value || '£0'}</span></div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="chart-card" style={{ minHeight: 'auto' }}>
                <div className="card-header">
                  <div className="card-title">{drilldownTrade ? "Breakdown by Trades" : "Sales Breakdown by Trade Groups"}</div>
                  {drilldownTrade && <button className="back-button" onClick={() => setDrilldownTrade(null)}><ArrowLeft size={14} /> Back</button>}
                </div>
                <ReactECharts option={getByTradeOption({ data, drilldownTrade })} theme={theme} onEvents={{ 'click': (p) => setDrilldownTrade(p.name) }} style={{ height: '280px' }} />
              </div>
              <div className="chart-card" style={{ minHeight: 'auto' }}>
                <div className="card-header"><div className="card-title">Rolling Collections (14m)</div></div>
                <ReactECharts option={getCollectionsTrendOption({ data })} theme={theme} style={{ height: '280px' }} />
              </div>
            </div>
          </section>

          <section className="dashboard-section">
            <h2 className="section-title-main"><Briefcase size={32} /> Operational Insights</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '12px' }}>
              <div className="chart-card">
                <div className="card-header"><div className="card-title">AJV Trend</div></div>
                <ReactECharts option={getAJVOption({ data })} theme={theme} style={{ height: '300px' }} />
              </div>
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title">Job Type Distribution</div>
                  {donutDrill && <button className="back-button" onClick={() => setDonutDrill(null)}><ArrowLeft size={14} /> Back</button>}
                </div>
                <ReactECharts option={getJobTypeOption({ data, donutDrill })} theme={theme} style={{ height: '300px' }} onEvents={{ 'click': (p) => setDonutDrill(p.name) }} />
              </div>
              <div className="chart-card">
                <div className="card-header"><div className="card-title">Job Type Revenue</div></div>
                <ReactECharts option={getJobTypeSalesOption({ data })} theme={theme} style={{ height: '300px' }} />
              </div>
            </div>
          </section>

          <div className="section-divider" />

          <section className="dashboard-section">
            <h2 className="section-title-main"><Users size={32} /> Service Appointments</h2>
            {insights.review_rating && <BigInsight content={insights.review_rating} />}
            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr', gap: '12px', marginTop: '12px' }}>
              <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ flex: 1 }}>
                  <div className="card-title" style={{ fontSize: '13px', color: COLORS.textMuted, textTransform: 'uppercase', marginBottom: '8px' }}>Today's Activity</div>
                  <ReactECharts option={getSASummaryOption({ summaryData: data.sas.summary.today })} theme={theme} style={{ height: '140px' }} />
                </div>
                <div style={{ flex: 1, borderTop: `1px solid ${COLORS.border}`, paddingTop: '12px' }}>
                  <div className="card-title" style={{ fontSize: '13px', color: COLORS.textMuted, textTransform: 'uppercase', marginBottom: '8px' }}>Monthly Total</div>
                  <ReactECharts option={getSASummaryOption({ summaryData: data.sas.summary.month })} theme={theme} style={{ height: '140px' }} />
                </div>
              </div>
              <div className="chart-card">
                <div className="card-header"><div className="card-title">Monthly Breakdown by Trade Groups</div></div>
                <ReactECharts option={getSATradesOption({ data })} theme={theme} style={{ height: '320px' }} />
                <InsightCapsule content={insights.top_trade_sa} />
              </div>
            </div>
          </section>

          <section className="dashboard-section" style={{ marginBottom: '40px' }}>
            <h2 className="section-title-main"><Briefcase size={32} /> Outstanding Debt</h2>
            <div className="chart-card">
              <div className="card-header"><div className="card-title">Outstanding Aging Analysis</div></div>
              <ReactECharts option={getAgingOption({ data })} theme={theme} style={{ height: '350px' }} />
              <InsightCapsule content={insights.outstanding} />
            </div>
          </section>
        </div>
      </main>

      <div className={`side-panel ${sidePanelOpen ? 'open' : ''}`}>
        <button className="close-panel" onClick={() => setSidePanelOpen(false)}><X size={20} /></button>
        <h2 style={{ color: COLORS.textMain, fontWeight: '900', marginBottom: '8px' }}>{selectedPoint?.name} Drill-down</h2>
        <p style={{ color: COLORS.textMuted, marginBottom: '32px' }}>Details for selected period</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {data.sales.trades.slice(0, 10).map((t, idx) => (
            <div key={idx} style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', border: `1px solid ${COLORS.border}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: '700' }}>{t.name}</span>
                <span style={{ color: COLORS.purple, fontWeight: '800' }}>£{(t.value / 1000).toFixed(0)}k</span>
              </div>
              <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${(t.value / 600000) * 100}%`, background: COLORS.purple }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default App;