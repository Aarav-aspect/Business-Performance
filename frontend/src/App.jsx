import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  TrendingUp, Users, Briefcase, FileText, CreditCard, X, Download, ChevronRight, Search, ArrowLeft, Calendar, Layers,
  Home, UserCircle, LogOut, BarChart2
} from 'lucide-react';
import InitialLoader from './components/InitialLoader/InitialLoader';

// --- HomeOwner region filtering ---
const HOMEOWNER_SF_VALUE = 'Home Owner';
const HOMEOWNER_REGIONS = ['Central', 'East', 'North West', 'South West'];

// --- Insurance sectors (hidden from sector dropdown, shown as account type button) ---
const INSURANCE_SECTORS = ['Insurance Commercial', 'Insurance Domestic', 'Insurance Utilities'];

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

// --- Formatters ---

const formatCurrency = (val) => new Intl.NumberFormat('en-GB', {
  style: 'currency',
  currency: 'GBP',
  maximumFractionDigits: 0
}).format(val);

const formatMonthLabel = (value) => {
  if (!value) return '';

  // Handle "Jan 25" format (already correct)
  if (/^[A-Z][a-z]{2} \d{2}$/.test(value)) return value;

  // Handle "January 2025" or similar full names
  const normalizedValue = /^\d{4}-\d{2}$/.test(value) ? `${value}-01` : value;
  const parsedDate = new Date(normalizedValue);

  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[parsedDate.getMonth()];
  const year = parsedDate.getFullYear().toString().slice(-2);

  return `${month} ${year}`;
};

// --- Helper Components ---

const KPICard = ({ label, value, trend, color = COLORS.purple, subValue }) => {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value-row">
        <div className="kpi-value">{value}</div>
        <div className="kpi-trend" style={{ color: trend.includes('+') ? COLORS.green : COLORS.red }}>{trend}</div>
      </div>
      {subValue && (
        <div style={{ fontSize: '11px', color: COLORS.textMuted, marginTop: '4px', fontWeight: '600' }}>
          {subValue}
        </div>
      )}
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
      return `${d.name}<br/>${d.marker} ${d.seriesName}: <b>${formatCurrency(d.value)}</b>`;
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
    axisLabel: { formatter: v => formatCurrency(v), color: COLORS.textMain, fontWeight: 'bold' },
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
        formatter: (p) => formatCurrency(p.value),
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
      return `${formatMonthLabel(d.name)}<br/>${d.marker} Collections: <b>${formatCurrency(d.value)}</b>`;
    }
  },
  grid: { left: '3%', right: '4%', bottom: '5%', top: '15%', containLabel: true },
  xAxis: {
    type: 'category',
    data: data.coll?.history?.map(d => d.month) || [],
    axisLabel: {
      color: COLORS.textMain,
      fontSize: 11,
      fontWeight: 'bold',
      formatter: value => formatMonthLabel(value)
    }
  },
  yAxis: {
    type: 'value',
    axisLabel: { formatter: v => formatCurrency(v), color: COLORS.textMain, fontWeight: 'bold' },
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
      formatter: (p) => formatCurrency(p.value),
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
  const target = data.sum?.current_revenue_raw || data.sum?.net_sales_raw || 1;
  const percentage = Math.min((current / target) * 100, 100);

  return {
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        center: ['50%', '80%'],
        radius: '130%',
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
          offsetCenter: [0, '-110%'],
          fontWeight: '900',
          fontSize: 22,
          color: COLORS.textMain,
          formatter: '{value}%'
        }
      }
    ]
  };
};

const TRADE_GAUGE_COLORS = [
  '#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6',
];

const getTradeGaugeOption = (value, total, color) => {
  const pct = total > 0 ? Math.min(Math.round((value / total) * 100), 100) : 0;
  return {
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      center: ['50%', '72%'],
      radius: '115%',
      pointer: { show: true, length: '60%', width: 4, itemStyle: { color } },
      progress: { show: true, roundCap: true, width: 10, itemStyle: { color } },
      axisLine: { lineStyle: { width: 10, color: [[1, '#f1f5f9']] } },
      splitLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      data: [{ value: pct }],
      detail: {
        offsetCenter: [0, '-105%'],
        fontWeight: '900',
        fontSize: 18,
        color: COLORS.textMain,
        formatter: '{value}%',
      },
    }],
  };
};

const getAgingOption = ({ data }) => {
  const buckets = data.out?.aging?.by_type || {};
  const categories = ['Cash', 'Credit'];
  const values = categories.map(cat => buckets[cat] || 0);

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p) => {
        const d = p[0];
        return `${d.name}<br/>${d.marker} ${d.seriesName}: <b>${formatCurrency(d.value)}</b>`;
      }
    },
    grid: { left: '3%', right: '10%', bottom: '5%', top: '5%', containLabel: true },
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
      label: { show: true, position: 'right', formatter: p => formatCurrency(p.value), fontWeight: '900', fontSize: 11, color: COLORS.textMain }
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
        return `${formatMonthLabel(d.name)}<br/>${d.marker} AJV: <b>£${Math.round(d.value)}</b>`;
      }
    },
    grid: { left: '2%', right: '4%', bottom: '8%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ajvData.map(d => d.month),
      axisLabel: {
        color: COLORS.textMain,
        fontWeight: 'bold',
        formatter: value => formatMonthLabel(value)
      }
    },
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

  let sortedTrades = [...rawData]
    .filter(t => t.name !== 'Other' && t.value > 0)
    .sort((a, b) => a.value - b.value);
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p) => {
        const d = p[0];
        return `${d.name}<br/>${d.marker} Value: <b>${formatCurrency(d.value)}</b>`;
      }
    },
    grid: { left: '2%', right: '12%', bottom: '2%', top: '2%', containLabel: true },
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
      label: { show: true, position: 'right', formatter: p => formatCurrency(p.value), color: COLORS.textMain, fontWeight: 'bold' }
    }]
  };
};

const getJobTypeOption = ({ data, donutDrill }) => {
  let fmtData = [];
  if (donutDrill && data.sas.type_trade_split) {
    const split = data.sas.type_trade_split[donutDrill] || {};
    fmtData = Object.entries(split).map(([name, value]) => ({ name, value })).filter(d => d.name !== 'Other');
  } else {
    fmtData = data.sas.sa_job_types || [];
  }

  const total = fmtData.reduce((a, b) => a + b.value, 0);

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        return `${p.marker} ${p.name}: <b>${formatCurrency(p.value)}</b> (${Math.round(p.percent)}%)`;
      }
    },
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: `TOTAL\n${donutDrill ? formatCurrency(total) : total}`,
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
          return `${params.name}: ${formatCurrency(params.value)}`;
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

const TRADE_COLORS = [
  COLORS.purple, COLORS.blue, COLORS.purpleLight, COLORS.blueDark,
  '#a78bfa', '#60a5fa', '#7c3aed', '#1d4ed8'
];

const getTradeColor = (() => {
  const cache = {};
  let idx = 0;
  return (name) => {
    if (!(name in cache)) cache[name] = TRADE_COLORS[idx++ % TRADE_COLORS.length];
    return cache[name];
  };
})();

const getClientSplitOption = ({ data }) => {
  const split = data.sas.client_split || { new: 0, existing: 0, total: 0 };
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.marker} ${p.name}: <b>${p.value}</b> (${Math.round(p.percent)}%)`
    },
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: `TOTAL\n${split.total}`,
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
        formatter: (p) => `${p.name}: ${p.value}`,
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
      data: [
        { name: 'New Customers', value: split.new, itemStyle: { color: COLORS.purple } },
        { name: 'Existing Customers', value: split.existing, itemStyle: { color: COLORS.blue } }
      ]
    }]
  };
};

const getJobTypeTradeCountsOption = ({ data, donutDrill }) => {
  const counts = data.sas.sa_type_trade_counts?.[donutDrill] || {};
  const items = Object.entries(counts)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([name, value]) => ({
      name,
      value,
      itemStyle: { color: getTradeColor(name) }
    }));
  const total = items.reduce((a, b) => a + b.value, 0);

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.marker} ${p.name}: <b>${p.value}</b> (${Math.round(p.percent)}%)`
    },
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: `TOTAL\n${total}`,
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
        formatter: (p) => `${p.name}: ${p.value}`,
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
      data: items
    }]
  };
};

const getJobTypeRevenueDrillOption = ({ data, revenueDrill }) => {
  const split = data.sas.type_trade_split?.[revenueDrill] || {};
  const items = Object.entries(split)
    .filter(([, v]) => v > 0)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([name, value]) => ({
      name,
      value,
      itemStyle: { color: getTradeColor(name) }
    }));
  const total = items.reduce((a, b) => a + b.value, 0);

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.marker} ${p.name}: <b>${formatCurrency(p.value)}</b> (${Math.round(p.percent)}%)`
    },
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: `TOTAL\n${formatCurrency(total)}`,
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
        formatter: (p) => `${p.name}: ${formatCurrency(p.value)}`,
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
      data: items
    }]
  };
};

const getJobTypeSalesOption = ({ data }) => {
  const srcData = data.sas.month_split || [];
  const reactive = srcData.find(d => d.name === 'Reactive') || { sales: 0 };
  const fixed = srcData.find(d => d.name === 'Fixed Price') || { sales: 0 };
  const total = (reactive.sales || 0) + (fixed.sales || 0);

  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.marker} ${p.name}: <b>${formatCurrency(p.value)}</b> (${Math.round(p.percent)}%)`
    },
    graphic: [{
      type: 'text',
      left: 'center',
      top: 'center',
      style: {
        text: `TOTAL\n${formatCurrency(total)}`,
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
        formatter: (p) => `${p.name}: ${formatCurrency(p.value)}`,
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
      data: [
        { name: 'Reactive', value: reactive.sales || 0, itemStyle: { color: COLORS.blue } },
        { name: 'Fixed Price', value: fixed.sales || 0, itemStyle: { color: COLORS.purple } }
      ]
    }]
  };
};

// --- Sidebar Navigation ---

const NAV_ITEMS = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'performance', label: 'Performance', icon: BarChart2 },
  { id: 'customer-profile', label: 'Customer Profile', icon: UserCircle },
];

const Sidebar = ({ activeTab, setActiveTab }) => (
  <aside className="sidebar">
    <div className="sidebar-logo">
      <img src="/Aspect_Logo.svg" alt="Aspect Logo" style={{ height: '28px' }} />
    </div>
    <nav className="sidebar-nav">
      {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          className={`sidebar-item${activeTab === id ? ' active' : ''}`}
          onClick={() => setActiveTab(id)}
        >
          <Icon size={18} />
          {label}
        </button>
      ))}
    </nav>
    <div className="sidebar-footer">
      <div className="sidebar-user">
        <div className="sidebar-user-avatar">AD</div>
        <div className="sidebar-user-info">
          <span className="sidebar-user-name">Ankit Dash</span>
          <span className="sidebar-user-role">Administrator</span>
        </div>
      </div>
      <button className="sidebar-logout">
        <LogOut size={16} />
        Log out
      </button>
    </div>
  </aside>
);

// --- Main Application ---

const App = () => {
  const [activeTab, setActiveTab] = useState('performance');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [salesView, setSalesView] = useState('monthly');
  const [collFlipped, setCollFlipped] = useState(false);
  const [drilldownTrade, setDrilldownTrade] = useState(null);
  const [donutDrill, setDonutDrill] = useState(null);
  const [revenueDrill, setRevenueDrill] = useState(null);
  const [insights, setInsights] = useState({});
  const [allSectors, setAllSectors] = useState([]);
  const [selectedSectors, setSelectedSectors] = useState([]);
  const [pendingSectors, setPendingSectors] = useState([]);
  const [sectorDropdownOpen, setSectorDropdownOpen] = useState(false);
  const sectorDropdownRef = React.useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (sectorDropdownRef.current && !sectorDropdownRef.current.contains(e.target)) {
        setSectorDropdownOpen(false);
        setPendingSectors(selectedSectors);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchSectors = React.useCallback(() => {
    fetch('http://localhost:8000/api/stats/sectors')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          // Replace the raw "HomeOwner" sector with 4 regional sub-options
          const expanded = [];
          for (const s of data) {
            if (s === HOMEOWNER_SF_VALUE) {
              HOMEOWNER_REGIONS.forEach(r => expanded.push(`${HOMEOWNER_SF_VALUE} - ${r}`));
            } else {
              expanded.push(s);
            }
          }
          setAllSectors(expanded);
          setPendingSectors(prev => prev.length === 0 ? [] : prev);
        }
      })
      .catch(err => console.warn('Sectors fetch failed:', err));
  }, []);

  useEffect(() => { fetchSectors(); }, [fetchSectors]);

  useEffect(() => {
    const API_BASE = 'http://localhost:8000/api';
    const fetchAll = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (selectedSectors.length > 0) {
          const homeownerSubSelected = selectedSectors.filter(s => s.startsWith(`${HOMEOWNER_SF_VALUE} - `));
          const regularSectors = selectedSectors.filter(s => !s.startsWith(`${HOMEOWNER_SF_VALUE} - `));
          if (homeownerSubSelected.length > 0) {
            // Add the base SF sector value for homeowner sub-options
            regularSectors.push(HOMEOWNER_SF_VALUE);
            // Extract region parts (e.g. "HomeOwner - Central" -> "Central")
            const regions = homeownerSubSelected.map(s => s.slice(`${HOMEOWNER_SF_VALUE} - `.length));
            params.set('homeowner_region', regions.join(','));
          }
          if (regularSectors.length > 0) params.set('sectors', regularSectors.join(','));
        }
        // Always exclude Key Account types — this app is for Core accounts only
        params.set('account_type', 'Cash,Credit');
        const qs = params.toString() ? `?${params.toString()}` : '';
        const fetchJson = async (url, retries = 8, delay = 3000) => {
          for (let i = 0; i < retries; i++) {
            const r = await fetch(url);
            const json = await r.json();
            if (r.status === 503 && json.warming) {
              await new Promise(res => setTimeout(res, delay));
              continue;
            }
            return json;
          }
          throw new Error(`Server still warming after ${retries} retries`);
        };
        const [sum, sales, jobs, coll, out, sas, insightRes] = await Promise.all([
          fetchJson(`${API_BASE}/stats/summary${qs}`),
          fetchJson(`${API_BASE}/stats/sales${qs}`),
          fetchJson(`${API_BASE}/stats/jobs${qs}`),
          fetchJson(`${API_BASE}/stats/collections${qs}`),
          fetchJson(`${API_BASE}/stats/outstanding${qs}`),
          fetchJson(`${API_BASE}/stats/sas${qs}`),
          fetchJson(`${API_BASE}/stats/insights${qs}`),
        ]);
        setData({ sum, sales, jobs, coll, out, sas });
        setInsights(insightRes);
        setLoading(false);
      } catch (e) { console.error(e); }
    };
    fetchAll();
  }, [selectedSectors]);

  if (loading) return <InitialLoader text="Initializing Aspect Dashboard..." />;

  return (
    <div className="dashboard-wrapper">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="main-viewport" style={{ paddingBottom: '60px' }}>
        {activeTab === 'home' && (
          <div className="tab-placeholder">
            <div className="tab-placeholder-icon"><Home size={28} /></div>
            <h2>Home</h2>
            <p>Your home overview will appear here.</p>
          </div>
        )}
        {activeTab === 'customer-profile' && (
          <div className="tab-placeholder">
            <div className="tab-placeholder-icon"><UserCircle size={28} /></div>
            <h2>Customer Profile</h2>
            <p>Customer profile details will appear here.</p>
          </div>
        )}
        {activeTab === 'performance' && <>
        <header className="dashboard-header">
          <div />
          <div className="header-controls">
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

          <div ref={sectorDropdownRef} style={{ position: 'relative' }}>
              <button
                onClick={() => setSectorDropdownOpen(o => { if (!o) { setPendingSectors(selectedSectors); if (allSectors.length === 0) fetchSectors(); } return !o; })}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 14px',
                  background: selectedSectors.length > 0 ? COLORS.purple : 'rgba(255, 255, 255, 0.5)',
                  border: `1px solid ${selectedSectors.length > 0 ? COLORS.purple : COLORS.border}`,
                  borderRadius: '10px',
                  fontSize: '12px',
                  color: selectedSectors.length > 0 ? '#fff' : COLORS.textMain,
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                <Layers size={14} />
                Sector: <span style={{ color: selectedSectors.length > 0 ? '#fff' : COLORS.purple }}>
                  {selectedSectors.length === 0 ? 'All Sectors' : selectedSectors.length === 1 ? selectedSectors[0] : `${selectedSectors.length} Selected`}
                </span>
              </button>
              {sectorDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 8px)',
                  right: 0,
                  background: '#fff',
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: '12px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                  zIndex: 1000,
                  width: '230px',
                  display: 'flex',
                  flexDirection: 'column',
                  maxHeight: '420px'
                }}>
                  <div style={{ padding: '10px 14px', borderBottom: `1px solid ${COLORS.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: COLORS.textMuted, textTransform: 'uppercase' }}>Filter by Sector</span>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button onClick={() => setPendingSectors([...allSectors])} style={{ fontSize: '11px', color: COLORS.purple, fontWeight: '700', background: 'none', border: 'none', cursor: 'pointer' }}>All</button>
                      {pendingSectors.length > 0 && (
                        <button onClick={() => setPendingSectors([])} style={{ fontSize: '11px', color: COLORS.textMuted, fontWeight: '700', background: 'none', border: 'none', cursor: 'pointer' }}>Clear</button>
                      )}
                    </div>
                  </div>
                  <div style={{ overflowY: 'auto', flex: 1 }}>
                    {allSectors.length === 0 && (
                      <div style={{ padding: '16px 14px', fontSize: '12px', color: COLORS.textDim, textAlign: 'center' }}>
                        Loading sectors…
                      </div>
                    )}
                    {allSectors.map(sector => (
                      <label key={sector} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        padding: '7px 14px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        color: COLORS.textMain,
                        fontWeight: pendingSectors.includes(sector) ? '700' : '500',
                        background: pendingSectors.includes(sector) ? 'rgba(99, 102, 241, 0.06)' : 'transparent'
                      }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.06)'}
                        onMouseLeave={e => e.currentTarget.style.background = pendingSectors.includes(sector) ? 'rgba(99, 102, 241, 0.06)' : 'transparent'}
                      >
                        <input
                          type="checkbox"
                          checked={pendingSectors.includes(sector)}
                          onChange={() => setPendingSectors(prev =>
                            prev.includes(sector) ? prev.filter(s => s !== sector) : [...prev, sector]
                          )}
                          style={{ accentColor: COLORS.purple, width: '14px', height: '14px' }}
                        />
                        {sector}
                      </label>
                    ))}
                  </div>
                  <div style={{ padding: '10px 14px', borderTop: `1px solid ${COLORS.border}`, flexShrink: 0 }}>
                    <button
                      onClick={() => { setSelectedSectors(pendingSectors); setSectorDropdownOpen(false); }}
                      style={{
                        width: '100%',
                        padding: '8px',
                        background: COLORS.purple,
                        color: '#fff',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '13px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      Apply{pendingSectors.length > 0 ? ` (${pendingSectors.length})` : ''}
                    </button>
                  </div>
                </div>
              )}
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
          <KPICard
            label="Net Sales"
            value={data.sum.net_sales.value}
            trend={data.sum.net_sales.trend}
            color={COLORS.purple}
            subValue={`Total Invoiced: ${formatCurrency(data.sum.net_billed_raw)}`}
          />
          <KPICard
            label="Total Credit"
            value={data.sum.total_credit?.value || "£0"}
            trend={data.sum.total_credit?.trend || "MTD Credit"}
            color={COLORS.teal}
            subValue={data.sum.total_credit?.credits_this_invoice != null
              ? `This month's invoices: ${formatCurrency(data.sum.total_credit.credits_this_invoice)} | Prior invoices: ${formatCurrency(data.sum.total_credit.credits_prev_invoice)}`
              : null}
          />
          <KPICard label="Outstanding" value={data.sum.outstanding_amount.value} trend={data.sum.outstanding_amount.trend} color={COLORS.pink} />
          <KPICard
            label="AJV"
            value={(() => { const ajv = data.out?.ajv || []; const cur = ajv[ajv.length - 1]; return cur ? `£${Math.round(cur.value).toLocaleString()}` : '£0'; })()}
            trend="↑ MTD"
            color={COLORS.blue}
            subValue={(() => { const ajv = data.out?.ajv || []; const prev = ajv[ajv.length - 2]; return prev ? `Last month: £${Math.round(prev.value).toLocaleString()}` : null; })()}
          />
        </div>

        <div className="view-container">
          <section className="dashboard-section">
            <h2 className="section-title-main"><TrendingUp size={32} /> Sales & Collections Performance</h2>
            <div className="sales-grid">
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontSize: '11px', fontWeight: '600', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Sales Today</span>
                      <span style={{ fontSize: '22px', fontWeight: '800', color: COLORS.textMain, letterSpacing: '-0.5px' }}>{data.sales?.today || '£0'}</span>
                    </div>
                  </div>
                  <div className="toggle-group">
                    <button className={`toggle-btn ${salesView === 'monthly' ? 'active' : ''}`} onClick={() => setSalesView('monthly')}>Monthly</button>
                    <button className={`toggle-btn ${salesView === 'quarterly' ? 'active' : ''}`} onClick={() => setSalesView('quarterly')}>Quarterly</button>
                  </div>
                </div>
                <ReactECharts option={getSalesOption({ salesView, data })} theme={theme} onEvents={{ 'click': (p) => { setSelectedPoint(p); setSidePanelOpen(true); } }} style={{ height: '350px' }} />
                <InsightCapsule content={insights.sales} />
              </div>
              {/* Collections card — front (hidden when expanded) */}
              {!collFlipped && (
                <div className="chart-card" style={{ display: 'flex', flexDirection: 'column' }}>
                  <div className="card-header">
                    <div className="card-title" style={{ fontSize: '13px', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Collections on Invoiced</div>
                    <button onClick={() => setCollFlipped(true)} style={{ fontSize: '11px', fontWeight: '600', color: COLORS.purple, background: 'none', border: `1px solid ${COLORS.purple}`, borderRadius: '6px', padding: '4px 10px', cursor: 'pointer', letterSpacing: '0.02em' }}>View Details</button>
                  </div>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '10px' }}>
                    <ReactECharts option={getCollectionsProgressOption({ data })} theme={theme} style={{ height: '240px', width: '100%' }} />
                    <div style={{ textAlign: 'center', marginTop: '10px' }}>
                      <div style={{ fontSize: '24px', fontWeight: '900', color: COLORS.textMain }}>{formatCurrency(data.coll?.total || 0)}</div>
                      <div style={{ fontSize: '12px', color: COLORS.textMuted }}>Current Revenue: <span
                        style={{ fontWeight: '700', borderBottom: `1px dashed ${COLORS.textDim}`, cursor: 'default' }}
                        title={`This month invoiced (${formatCurrency(data.sum?.net_billed_raw || 0)}) − Credits on this month's invoices (${formatCurrency(data.sum?.total_credit?.credits_this_invoice || 0)})`}
                      >{data.sum?.current_revenue_raw != null ? formatCurrency(data.sum.current_revenue_raw) : (data.sum?.net_sales?.value || '£0')}</span></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Collections modal overlay — flips in, centered, blurred backdrop */}
            {collFlipped && (() => {
              const groups = data.coll?.by_trade_group || [];
              const total = data.coll?.total || 0;
              const cells = [...groups];
              while (cells.length < 6) cells.push(null);
              return (
                <div
                  onClick={(e) => { if (e.target === e.currentTarget) setCollFlipped(false); }}
                  style={{
                    position: 'fixed', inset: 0, zIndex: 1000,
                    background: 'rgba(15, 23, 42, 0.45)',
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    animation: 'collBackdropIn 0.35s ease both',
                  }}
                >
                  <div className="chart-card" style={{
                    width: 'min(1300px, 96vw)',
                    maxHeight: '92vh',
                    overflowY: 'auto',
                    animation: 'collModalFlip 0.5s cubic-bezier(0.4,0.2,0.2,1) both',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.28)',
                  }}>
                    <div className="card-header">
                      <div style={{ fontSize: '13px', fontWeight: '700', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Collections on Invoiced</div>
                      <button onClick={() => setCollFlipped(false)} style={{ fontSize: '11px', fontWeight: '600', color: COLORS.slate, background: '#f8fafc', border: `1px solid ${COLORS.border}`, borderRadius: '6px', padding: '5px 14px', cursor: 'pointer' }}>✕ Close</button>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', padding: '20px 8px 12px' }}>
                      {cells.map((g, i) => g ? (
                        <div key={g.name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '20px 12px 24px' }}>
                          <ReactECharts
                            option={getTradeGaugeOption(g.collected, g.invoiced || g.collected, TRADE_GAUGE_COLORS[i % TRADE_GAUGE_COLORS.length])}
                            theme={theme}
                            style={{ height: '240px', width: '100%' }}
                          />
                          <div style={{ textAlign: 'center', marginTop: '-4px' }}>
                            <div style={{ fontSize: '13px', fontWeight: '700', color: COLORS.textMain, lineHeight: 1.3 }}>{g.name}</div>
                            <div style={{ fontSize: '16px', fontWeight: '900', color: TRADE_GAUGE_COLORS[i % TRADE_GAUGE_COLORS.length], marginTop: '3px' }}>{formatCurrency(g.collected)}</div>
                            <div style={{ fontSize: '11px', color: COLORS.textDim, marginTop: '2px' }}>of {formatCurrency(g.invoiced)}</div>
                          </div>
                        </div>
                      ) : (
                        <div key={`empty-${i}`} style={{ height: '200px', borderRadius: '8px', background: '#f8fafc', border: `1px dashed ${COLORS.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <span style={{ fontSize: '11px', color: COLORS.textDim }}>—</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })()}

            <div className="split-grid" style={{ gridTemplateColumns: '3.5fr 6.5fr', alignItems: 'stretch' }}>
              <div className="chart-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div className="card-header">
                  <div className="card-title">{drilldownTrade ? "Breakdown by Trades" : "Sales Breakdown by Trade Groups"}</div>
                  {drilldownTrade && <button className="back-button" onClick={() => setDrilldownTrade(null)}><ArrowLeft size={14} /> Back</button>}
                </div>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
                  <ReactECharts
                    option={getByTradeOption({ data, drilldownTrade })}
                    theme={theme}
                    onEvents={{ 'click': (p) => setDrilldownTrade(p.name) }}
                    style={{ height: '550px', width: '100%' }}
                  />
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="chart-card" style={{ minHeight: 'auto', flex: 1 }}>
                  <div className="card-header"><div className="card-title">Rolling Collections (14m)</div></div>
                  <ReactECharts option={getCollectionsTrendOption({ data })} theme={theme} style={{ height: '240px' }} />
                </div>
                <div className="chart-card" style={{ minHeight: 'auto', flex: 1 }}>
                  <div className="card-header"><div className="card-title">AJV Trend</div></div>
                  <ReactECharts option={getAJVOption({ data })} theme={theme} style={{ height: '240px' }} />
                </div>
              </div>
            </div>
          </section>

          <section className="dashboard-section">
            <h2 className="section-title-main"><Briefcase size={32} /> Operational Insights</h2>
            <div className="ops-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title">{donutDrill ? `${donutDrill} — Jobs by Trade Group` : 'Job Type Distribution'}</div>
                  {donutDrill && <button className="back-button" onClick={() => setDonutDrill(null)}><ArrowLeft size={14} /> Back</button>}
                </div>
                {donutDrill ? (
                  <ReactECharts option={getJobTypeTradeCountsOption({ data, donutDrill })} theme={theme} style={{ height: '320px' }} />
                ) : (
                  <ReactECharts option={getJobTypeOption({ data, donutDrill: null })} theme={theme} style={{ height: '320px' }} onEvents={{ 'click': (p) => setDonutDrill(p.name) }} />
                )}
              </div>
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title">{revenueDrill ? `${revenueDrill} — Revenue by Trade Group` : 'Job Type Revenue'}</div>
                  {revenueDrill && <button className="back-button" onClick={() => setRevenueDrill(null)}><ArrowLeft size={14} /> Back</button>}
                </div>
                {revenueDrill ? (
                  <ReactECharts option={getJobTypeRevenueDrillOption({ data, revenueDrill })} theme={theme} style={{ height: '320px' }} />
                ) : (
                  <ReactECharts option={getJobTypeSalesOption({ data })} theme={theme} style={{ height: '320px' }} onEvents={{ 'click': (p) => setRevenueDrill(p.name) }} />
                )}
                {(() => {
                  const srcData = data.sas?.month_split || [];
                  const reactive = srcData.find(d => d.name === 'Reactive')?.sales || 0;
                  const fixed = srcData.find(d => d.name === 'Fixed Price')?.sales || 0;
                  const total = reactive + fixed;
                  if (total === 0) return null;

                  const dominant = reactive >= fixed ? 'Reactive' : 'Fixed Price';
                  const domValue = Math.max(reactive, fixed);
                  const percentage = Math.round((domValue / total) * 100);

                  return (
                    <InsightCapsule content={`${dominant} jobs make up the majority of revenue this month, accounting for ${percentage}% of total job type sales (${formatCurrency(domValue)}).`} />
                  );
                })()}
              </div>
            </div>
          </section>

          <div className="section-divider" />

          <section className="dashboard-section">
            <h2 className="section-title-main"><Users size={32} /> Service Appointments</h2>
            {insights.review_rating && <BigInsight content={insights.review_rating} />}
            <div style={{ marginTop: '12px' }}>
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title">Job Distribution by Customers</div>
                </div>
                <ReactECharts option={getClientSplitOption({ data })} theme={theme} style={{ height: '400px' }} />
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
        </>}
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
                <span style={{ color: COLORS.purple, fontWeight: '800' }}>{formatCurrency(t.value)}</span>
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
