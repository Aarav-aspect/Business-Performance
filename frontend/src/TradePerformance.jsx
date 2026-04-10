import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactECharts from 'echarts-for-react';
import { toPng } from 'html-to-image';
import {
  TrendingUp, Users, Briefcase, FileText, CreditCard, X, Copy, Check, ChevronRight, Search, ArrowLeft, Calendar, Layers
} from 'lucide-react';
import InitialLoader from './components/InitialLoader/InitialLoader';

// --- Theme Synced with index.css ---
const COLORS = {
  purple: '#27549D',
  purpleDark: '#27549D',
  purpleLight: '#27549D',
  blue: '#f1fe27',
  blueDark: '#f1fe27',
  slate: '#475569',
  border: '#cbd5e1',
  cardBg: '#ffffff',
  textMuted: '#64748b',
  textDim: '#94a3b8',
  textMain: '#1e293b',
  green: '#10b981',
  red: '#ef4444',
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
  if (/^[A-Z][a-z]{2} \d{2}$/.test(value)) return value;
  const normalizedValue = /^\d{4}-\d{2}$/.test(value) ? `${value}-01` : value;
  const parsedDate = new Date(normalizedValue);
  if (Number.isNaN(parsedDate.getTime())) return value;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[parsedDate.getMonth()]} ${parsedDate.getFullYear().toString().slice(-2)}`;
};

const DEFAULT_START_MONTH = 'Jan 25';
const sliceFromMonth = (arr, dateKey = 'date') => {
  const idx = arr.findIndex(d => (d[dateKey] || d.month) === DEFAULT_START_MONTH);
  return idx >= 0 ? arr.slice(idx) : arr;
};

// --- Helper Components ---

const KPICard = ({ label, value, trend, color = COLORS.purple, subValue }) => (
  <div className="kpi-card">
    <div className="kpi-label">{label}</div>
    <div className="kpi-value-row">
      <div className="kpi-value">{value}</div>
    </div>
    {subValue && (
      <div style={{ fontSize: '11px', color: COLORS.textMuted, marginTop: '4px', fontWeight: '600' }}>
        {subValue}
      </div>
    )}
  </div>
);

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
      background: '#6366f1',
      borderRadius: '12px',
      padding: '12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <TrendingUp size={24} color="#fff" />
    </div>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: '11px', color: '#6366f1', fontWeight: '900', textTransform: 'uppercase', marginBottom: '4px', letterSpacing: '0.08em' }}>Review Information</div>
      <div style={{ fontSize: '15px', fontWeight: '700', color: COLORS.textMain, lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>{content}</div>
    </div>
  </div>
);

// --- Chart Option Generators ---

const getSalesOption = ({ salesView, data }) => {
  const sliced = salesView === 'monthly' ? sliceFromMonth(data.sales[salesView]) : data.sales[salesView];
  const hasTargets = sliced.some(d => d.target > 0);
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = params[0]?.name || '';
        for (const p of params) {
          html += `<br/>${p.marker} ${p.seriesName}: <b>${formatCurrency(p.value)}</b>`;
        }
        return html;
      }
    },
    legend: { show: false },
    grid: { left: '1%', right: '2%', bottom: '8%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: sliced.map(d => d.date),
      axisLabel: { color: COLORS.textMain, fontSize: 11, fontWeight: 'bold' },
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: v => v >= 1000000 ? `£${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `£${(v / 1000).toFixed(0)}K` : `£${v}`, color: COLORS.textMain, fontWeight: 'bold', fontSize: 11 },
    },
    series: [
      ...(hasTargets ? [{
        name: 'Target',
        data: sliced.map(d => d.target || null),
        type: 'line',
        symbol: 'none',
        connectNulls: false,
        lineStyle: { width: 2, color: 'rgba(39, 84, 157, 0.5)' },
        areaStyle: { color: 'rgba(39, 84, 157, 0.13)' },
        z: 1,
      }] : []),
      {
        name: 'Actual Sales',
        data: sliced.map(d => d.sales),
        type: 'line',
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 3, color: '#27549D' },
        itemStyle: { color: '#27549D' },
        label: {
          show: true,
          position: 'top',
          formatter: (p) => p.dataIndex === 0 ? '' : formatCurrency(p.value),
          color: COLORS.textMain,
          fontWeight: '900',
          fontSize: 11
        },
        areaStyle: { color: 'rgba(39, 84, 157, 0.35)' },
        z: 2,
      }
    ]
  };
};

const getDailyTargetOption = ({ data }) => {
  const dt = data.daily_target || {};
  const dailySales = dt.daily_sales || [];
  const monthlyTarget = dt.monthly_target || 0;
  const daysInMonth = dt.days_in_month || 30;
  const dailyTarget = monthlyTarget / daysInMonth;

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const now = new Date();
  const monthLabel = monthNames[now.getMonth()];
  const todayDay = now.getDate();

  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const labels = days.map(d => `${d} ${monthLabel}`);
  const targetCumulative = days.map(d => Math.round(dailyTarget * d));

  const salesMap = {};
  dailySales.forEach(s => { salesMap[s.day] = s.cumulative; });
  const salesCumulative = [];
  let lastVal = 0;
  for (let d = 1; d <= daysInMonth; d++) {
    if (d > todayDay) { salesCumulative.push(null); continue; }
    if (salesMap[d] != null) lastVal = salesMap[d];
    salesCumulative.push(lastVal);
  }

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        const lines = ps.filter(p => p.value != null).map(p => `${p.marker} ${p.seriesName}: ${formatCurrency(p.value)}`);
        return lines.length ? `${ps[0].name}<br/>` + lines.join('<br/>') : '';
      }
    },
    legend: { show: false },
    grid: { left: '1%', right: '3%', bottom: '8%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category', data: labels, boundaryGap: false,
      axisLabel: { color: COLORS.textMuted, fontSize: 9, interval: Math.floor(daysInMonth / 6) },
      axisLine: { show: false }, axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: COLORS.textMuted, fontSize: 10,
        formatter: v => v >= 1000000 ? `£${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `£${(v / 1000).toFixed(0)}K` : `£${v}`
      },
      splitLine: { lineStyle: { type: 'dashed', color: '#e5e5ea' } }
    },
    series: [
      {
        name: 'Target',
        type: 'line',
        data: targetCumulative,
        lineStyle: { width: 2, color: 'rgba(39, 84, 157, 0.5)' },
        areaStyle: { color: 'rgba(39, 84, 157, 0.13)' },
        symbol: 'none',
        z: 1,
      },
      {
        name: 'Actual Sales',
        type: 'line',
        data: salesCumulative,
        lineStyle: { width: 3, color: '#27549D' },
        areaStyle: { color: 'rgba(39, 84, 157, 0.15)' },
        symbol: 'none',
        z: 2,
      },
    ]
  };
};

const getCollectionsTrendOption = ({ data }) => {
  const sliced = sliceFromMonth(data.coll?.history || [], 'month');
  return {
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
      data: sliced.map(d => d.month),
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
      data: sliced.map(d => d.value),
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
      areaStyle: { color: 'rgba(39, 84, 157, 0.1)' }
    }]
  };
};

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
  '#27549D', '#f1fe27', '#10b981', '#f59e0b', '#27549D', '#27549D',
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
        offsetCenter: [0, '-110%'],
        fontWeight: '900',
        fontSize: 18,
        color: COLORS.textMain,
        formatter: '{value}%',
      },
    }],
  };
};

const getAgingOption = ({ data }) => {
  const regional = data.out?.aging_regional || {};
  const regions = regional.regions || [];
  const byType = regional.by_type || {};

  if (regions.length > 0 && Object.keys(byType).length > 0) {
    const categories = ['Cash', 'Credit'];
    return {
      tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>` + p.map(d => `${d.marker} ${d.seriesName}: <b>${formatCurrency(d.value)}</b>`).join('<br/>') },
      legend: { data: regions, top: 0, right: 0, textStyle: { fontSize: 11, fontWeight: '600', color: COLORS.textMain } },
      grid: { left: '3%', right: '12%', bottom: '5%', top: '12%', containLabel: true },
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', data: categories, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
      series: regions.map(r => ({
        name: r,
        type: 'bar',
        data: categories.map(cat => byType[r]?.[cat] || 0),
        itemStyle: { color: REGION_COLORS[r] || COLORS.purpleLight },
        label: { show: true, position: 'right', formatter: p => formatCurrency(p.value), fontWeight: '900', fontSize: 11, color: COLORS.textMain }
      }))
    };
  }

  // Fallback: no regional data
  const buckets = data.out?.aging?.by_type || {};
  const categories = ['Cash', 'Credit'];
  const values = categories.map(cat => buckets[cat] || 0);
  return {
    tooltip: { trigger: 'axis', formatter: (p) => { const d = p[0]; return `${d.name}<br/>${d.marker} ${d.seriesName}: <b>${formatCurrency(d.value)}</b>`; } },
    grid: { left: '3%', right: '10%', bottom: '5%', top: '5%', containLabel: true },
    xAxis: { type: 'value', show: false },
    yAxis: { type: 'category', data: categories, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
    series: [{ type: 'bar', data: values, itemStyle: { color: COLORS.purpleLight, borderRadius: 0 }, barWidth: '50%', label: { show: true, position: 'right', formatter: p => formatCurrency(p.value), fontWeight: '900', fontSize: 11, color: COLORS.textMain } }]
  };
};

const getAJVOption = ({ data }) => {
  const ajvData = sliceFromMonth(data.out?.ajv || [], 'month');
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
      axisLabel: { color: COLORS.textMain, fontWeight: 'bold', formatter: value => formatMonthLabel(value) }
    },
    yAxis: { type: 'value', min: (v) => Math.floor(v.min * 0.9 / 50) * 50, axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
    series: [{
      data: ajvData.map(d => d.value),
      type: 'line',
      smooth: false,
      itemStyle: { color: COLORS.purple },
      areaStyle: { color: 'rgba(39, 84, 157, 0.15)' },
      lineStyle: { width: 3 },
      symbolSize: 6,
      label: { show: true, position: 'top', formatter: p => `£${Math.round(p.value)}`, fontSize: 11, fontWeight: 'bold', color: COLORS.textMain }
    }]
  };
};

const REGION_COLORS = {
  'North': '#27549D',
  'South': '#ecfa2cfa',
  'East': '#27549D',
  'North West': '#ecfa2cfa',
  'South West': '#2182cdff',
};

const getRegionalAJVOption = ({ data }) => {
  const regional = data.out?.ajv_regional || [];
  if (!regional.length) return null;

  // Collect all months across all regions for a unified x-axis
  const monthSet = new Set();
  regional.forEach(r => {
    const sliced = sliceFromMonth(r.trend || [], 'month');
    sliced.forEach(d => monthSet.add(d.month));
  });
  // Sort months chronologically
  const monthOrder = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const allMonths = [...monthSet].sort((a, b) => {
    const [am, ay] = [a.split(' ')[0], parseInt(a.split(' ')[1])];
    const [bm, by] = [b.split(' ')[0], parseInt(b.split(' ')[1])];
    if (ay !== by) return ay - by;
    return monthOrder.indexOf(am) - monthOrder.indexOf(bm);
  });

  const series = regional.map(r => {
    const sliced = sliceFromMonth(r.trend || [], 'month');
    const valMap = {};
    sliced.forEach(d => { valMap[d.month] = d.value; });
    return {
      name: r.region,
      type: 'line',
      smooth: false,
      data: allMonths.map(m => valMap[m] ?? null),
      connectNulls: true,
      itemStyle: { color: REGION_COLORS[r.region] || COLORS.purple },
      lineStyle: { width: 3 },
      symbolSize: 6,
      label: { show: true, position: 'top', formatter: p => p.value != null ? `£${Math.round(p.value)}` : '', fontSize: 10, fontWeight: 'bold', color: COLORS.textMain },
    };
  });

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = `<b>${formatMonthLabel(params[0]?.name)}</b>`;
        params.forEach(p => {
          if (p.value != null) html += `<br/>${p.marker} ${p.seriesName}: <b>£${Math.round(p.value)}</b>`;
        });
        return html;
      }
    },
    legend: { data: regional.map(r => r.region), bottom: 0, textStyle: { color: COLORS.textMain, fontWeight: '600' } },
    grid: { left: '2%', right: '4%', bottom: '14%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: allMonths,
      axisLabel: { color: COLORS.textMain, fontWeight: 'bold', formatter: value => formatMonthLabel(value) }
    },
    yAxis: { type: 'value', min: (v) => Math.floor(v.min * 0.9 / 50) * 50, axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
    series,
  };
};

const getByRegionOption = ({ data, tradeMonthKey }) => {
  const salesByRegion = data.sas.sales_by_region || {};
  const regions = salesByRegion.regions || [];
  const byMonth = salesByRegion.by_month || [];

  if (!regions.length || !byMonth.length) return null;

  // Find the right month entry
  let entry;
  if (tradeMonthKey) {
    entry = byMonth.find(m => m.month_key === tradeMonthKey);
  } else {
    entry = byMonth[byMonth.length - 1]; // latest (current month)
  }
  if (!entry) return null;

  // Fixed order: North/South or East/North West/South West (reversed for bottom-to-top y-axis)
  const REGION_ORDER = { 'North': 0, 'South': 1, 'East': 0, 'North West': 1, 'South West': 2 };
  const rawData = regions
    .map(r => ({ name: r, value: entry.regions?.[r] || 0 }))
    .sort((a, b) => REGION_ORDER[b.name] - REGION_ORDER[a.name]);

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
      data: rawData.map(t => t.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: COLORS.textMain, fontWeight: 'bold' }
    },
    series: [{
      type: 'bar',
      data: rawData.map(t => ({
        value: t.value,
        itemStyle: { color: REGION_COLORS[t.name] || COLORS.purpleLight, borderRadius: 0 }
      })),
      barWidth: '50%',
      label: { show: true, position: 'right', formatter: p => formatCurrency(p.value), color: COLORS.textMain, fontWeight: '900', fontSize: 11 }
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
      formatter: (p) => `${p.marker} ${p.name}: <b>${formatCurrency(p.value)}</b> (${Math.round(p.percent)}%)`
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
      selectedOffset: 0,
      emphasis: { scale: false },
      itemStyle: { borderRadius: 0, borderColor: '#fff', borderWidth: 0 },
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
      labelLine: { show: true, length: 20, length2: 15, lineStyle: { color: COLORS.border, width: 2 } },
      data: fmtData.map((d, i) => ({
        ...d,
        itemStyle: { color: [COLORS.purple, COLORS.blue, COLORS.pink, COLORS.teal][i % 4] }
      }))
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
      selectedOffset: 0,
      emphasis: { scale: false },
      itemStyle: { borderRadius: 0, borderColor: '#fff', borderWidth: 0 },
      label: {
        show: true,
        position: 'outside',
        formatter: (p) => `${p.name}: ${p.value}`,
        color: COLORS.textMain,
        fontWeight: '900',
        fontSize: 12
      },
      labelLine: { show: true, length: 20, length2: 15, lineStyle: { color: COLORS.border, width: 2 } },
      data: [
        { name: 'New Customers', value: split.new, itemStyle: { color: COLORS.purple } },
        { name: 'Existing Customers', value: split.existing, itemStyle: { color: COLORS.blue } }
      ]
    }]
  };
};

const getJobTypeRegionalCountsOption = ({ data, donutDrill }) => {
  const regional = data.sas.job_type_regional || {};
  const counts = regional.counts_by_type?.[donutDrill] || {};
  const regionsList = regional.regions || [];
  const items = regionsList
    .filter(r => (counts[r] || 0) > 0)
    .map(name => ({
      name, value: counts[name] || 0,
      itemStyle: { color: REGION_COLORS[name] || COLORS.purple }
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
      selectedOffset: 0,
      emphasis: { scale: false },
      itemStyle: { borderRadius: 0, borderColor: '#fff', borderWidth: 0 },
      label: {
        show: true,
        position: 'outside',
        formatter: (p) => `${p.name}: ${p.value}`,
        color: COLORS.textMain,
        fontWeight: '900',
        fontSize: 12
      },
      labelLine: { show: true, length: 20, length2: 15, lineStyle: { color: COLORS.border, width: 2 } },
      data: items
    }]
  };
};

const getJobTypeRegionalRevenueOption = ({ data, revenueDrill }) => {
  const regional = data.sas.job_type_regional || {};
  const revenue = regional.revenue_by_type?.[revenueDrill] || {};
  const regionsList = regional.regions || [];
  const items = regionsList
    .filter(r => (revenue[r] || 0) > 0)
    .map(name => ({
      name, value: revenue[name] || 0,
      itemStyle: { color: REGION_COLORS[name] || COLORS.purple }
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
      selectedOffset: 0,
      emphasis: { scale: false },
      itemStyle: { borderRadius: 0, borderColor: '#fff', borderWidth: 0 },
      label: {
        show: true,
        position: 'outside',
        formatter: (p) => `${p.name}: ${formatCurrency(p.value)}`,
        color: COLORS.textMain,
        fontWeight: '900',
        fontSize: 12
      },
      labelLine: { show: true, length: 20, length2: 15, lineStyle: { color: COLORS.border, width: 2 } },
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
      selectedOffset: 0,
      emphasis: { scale: false },
      itemStyle: { borderRadius: 0, borderColor: '#fff', borderWidth: 0 },
      label: {
        show: true,
        position: 'outside',
        formatter: (p) => `${p.name}: ${formatCurrency(p.value)}`,
        color: COLORS.textMain,
        fontWeight: '900',
        fontSize: 12
      },
      labelLine: { show: true, length: 20, length2: 15, lineStyle: { color: COLORS.border, width: 2 } },
      data: [
        { name: 'Reactive', value: reactive.sales || 0, itemStyle: { color: COLORS.blue } },
        { name: 'Fixed Price', value: fixed.sales || 0, itemStyle: { color: COLORS.purple } }
      ]
    }]
  };
};


const TRADE_ICON_MAP = {
  'HVAC & Electrical': '/business-performance/HVACandElectrical.svg',
  'HVac & Electrical': '/business-performance/HVACandElectrical.svg',
  'Building Fabric': '/business-performance/BuildingFabric.svg',
  'Environmental Services': '/business-performance/environmental.svg',
  'Fire Safety': '/business-performance/FireSafety.svg',
  'Leak, Damp & Restoration': '/business-performance/LeakDetection.svg',
  'Plumbing & Drainage': '/business-performance/Drainageandplumbing.svg',
};

// --- Main Component ---

const TradePerformance = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [salesView, setSalesView] = useState('monthly');
  const [collFlipped, setCollFlipped] = useState(false);

  const [tradeMonthOffset, setTradeMonthOffset] = useState(0);
  const [donutDrill, setDonutDrill] = useState(null);
  const [revenueDrill, setRevenueDrill] = useState(null);
  const [agingDrillType, setAgingDrillType] = useState(null);
  const [agingDrillRegion, setAgingDrillRegion] = useState(null);
  const [insights, setInsights] = useState({});
  const dashboardRef = useRef(null);

  // Trade group / subgroup filter state (static, mirrors backend TRADE_SUBGROUPS)
  const tradeGroups = {
    'HVac & Electrical': ['Air Conditioning', 'Gas & Heating', 'Electrical'],
    'Building Fabric': ['Decoration', 'Roofing', 'Multi Trades', 'Project Management'],
    'Environmental Services': ['Gardening', 'Pest Control', 'Specialist Cleaning', 'Waste and Grease Management'],
    'Fire Safety': ['Fire Safety'],
    'Leak, Damp & Restoration': ['Leak Detection', 'Damp', 'Restoration'],
    'Plumbing & Drainage': ['Plumbing', 'Drainage'],
  };
  const [selectedTradeGroup, setSelectedTradeGroup] = useState('HVac & Electrical');
  const [tradeGroupDropdownOpen, setTradeGroupDropdownOpen] = useState(false);
  const tradeGroupDropdownRef = useRef(null);

  const [selectedTradeSubgroup, setSelectedTradeSubgroup] = useState('');
  const [tradeSubgroupDropdownOpen, setTradeSubgroupDropdownOpen] = useState(false);
  const tradeSubgroupDropdownRef = useRef(null);

  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(async () => {
    if (!dashboardRef.current) return;
    const pngUrl = await toPng(dashboardRef.current, {
      pixelRatio: 2,
      backgroundColor: '#eef1f6',
    });
    const res = await fetch(pngUrl);
    const blob = await res.blob();
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (tradeGroupDropdownRef.current && !tradeGroupDropdownRef.current.contains(e.target)) {
        setTradeGroupDropdownOpen(false);
      }
      if (tradeSubgroupDropdownRef.current && !tradeSubgroupDropdownRef.current.contains(e.target)) {
        setTradeSubgroupDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch dashboard data when filters change
  useEffect(() => {
    const API_BASE = '/business-performance/api';
    const fetchAll = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.set('account_type', 'Cash,Credit');
        if (selectedTradeGroup) params.set('trade_group', selectedTradeGroup);
        if (selectedTradeSubgroup) params.set('trade_subgroup', selectedTradeSubgroup);
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
        const dash = await fetchJson(`${API_BASE}/dashboard${qs}`);
        setData({
          sum: dash.summary,
          sales: dash.sales,
          jobs: dash.jobs,
          coll: dash.collections,
          out: dash.outstanding,
          sas: dash.sas,
          daily_target: dash.daily_target,
          wip: dash.wip,
        });
        setInsights(dash.insights);
        setLoading(false);
      } catch (e) { console.error(e); setLoading(false); }
    };
    fetchAll();
  }, [selectedTradeGroup, selectedTradeSubgroup]);

  if (loading) return <InitialLoader text="Initializing Aspect Dashboard..." />;

  const subgroups = selectedTradeGroup ? (tradeGroups[selectedTradeGroup] || []) : [];

  return (
    <div className="dashboard-wrapper">
      <main className="main-viewport" ref={dashboardRef} style={{ paddingBottom: '24px' }}>
        <header className="dashboard-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <img src="/business-performance/Aspect_Logo.svg" alt="Aspect" style={{ height: '36px' }} />
            <nav style={{ display: 'flex', gap: '4px' }}>
              <a href="/business-performance/sectorperformance" style={{ padding: '6px 14px', borderRadius: '8px', fontSize: '13px', fontWeight: '600', color: COLORS.textMuted, textDecoration: 'none' }}>Sector Performance</a>
              <a href="/business-performance/tradeperformance" style={{ padding: '6px 14px', borderRadius: '8px', fontSize: '13px', fontWeight: '700', color: '#fff', background: COLORS.purple, textDecoration: 'none' }}>Trade Performance</a>
            </nav>
          </div>
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

            {/* Trade Group Dropdown */}
            <div ref={tradeGroupDropdownRef} style={{ position: 'relative' }}>
              <button
                onClick={() => setTradeGroupDropdownOpen(o => !o)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 14px',
                  background: selectedTradeGroup ? COLORS.purple : 'rgba(255, 255, 255, 0.5)',
                  border: `1px solid ${selectedTradeGroup ? COLORS.purple : COLORS.border}`,
                  borderRadius: '10px',
                  fontSize: '12px',
                  color: selectedTradeGroup ? '#fff' : COLORS.textMain,
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                <Layers size={14} />
                Trade Group: <span style={{ color: selectedTradeGroup ? '#fff' : COLORS.purple }}>
                  {selectedTradeGroup || 'All Groups'}
                </span>
              </button>
              {tradeGroupDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 8px)',
                  right: 0,
                  background: '#fff',
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: '12px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                  zIndex: 1000,
                  width: '280px',
                  display: 'flex',
                  flexDirection: 'column',
                  maxHeight: '420px'
                }}>
                  <div style={{ padding: '10px 14px', borderBottom: `1px solid ${COLORS.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: COLORS.textMuted, textTransform: 'uppercase' }}>Trade Group</span>
                  </div>
                  <div style={{ overflowY: 'auto', flex: 1 }}>
                    {Object.keys(tradeGroups).map(group => (
                      <div key={group}
                        onClick={() => {
                          setSelectedTradeGroup(group);
                          setSelectedTradeSubgroup('');
                          setTradeGroupDropdownOpen(false);
                        }}
                        style={{
                          padding: '8px 14px',
                          cursor: 'pointer',
                          fontSize: '13px',
                          color: COLORS.textMain,
                          fontWeight: selectedTradeGroup === group ? '700' : '500',
                          background: selectedTradeGroup === group ? 'rgba(39, 84, 157, 0.06)' : 'transparent',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(39, 84, 157, 0.06)'}
                        onMouseLeave={e => e.currentTarget.style.background = selectedTradeGroup === group ? 'rgba(39, 84, 157, 0.06)' : 'transparent'}
                      >
                        {TRADE_ICON_MAP[group] && <img src={TRADE_ICON_MAP[group]} alt="" style={{ width: '20px', height: '20px' }} />}
                        {group}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Trade Subgroup Dropdown */}
            <div ref={tradeSubgroupDropdownRef} style={{ position: 'relative' }}>
              <button
                onClick={() => setTradeSubgroupDropdownOpen(o => !o)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 14px',
                  background: selectedTradeSubgroup ? COLORS.purple : 'rgba(255, 255, 255, 0.5)',
                  border: `1px solid ${selectedTradeSubgroup ? COLORS.purple : COLORS.border}`,
                  borderRadius: '10px',
                  fontSize: '12px',
                  color: selectedTradeSubgroup ? '#fff' : COLORS.textMain,
                  fontWeight: '600',
                  cursor: 'pointer',
                  opacity: subgroups.length === 0 ? 0.5 : 1,
                }}
                disabled={subgroups.length === 0}
              >
                <Layers size={14} />
                Trade Subgroup: <span style={{ color: selectedTradeSubgroup ? '#fff' : COLORS.purple }}>
                  {selectedTradeSubgroup || 'All Subgroups'}
                </span>
              </button>
              {tradeSubgroupDropdownOpen && subgroups.length > 0 && (
                <div style={{
                  position: 'absolute',
                  top: 'calc(100% + 8px)',
                  right: 0,
                  background: '#fff',
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: '12px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                  zIndex: 1000,
                  width: '260px',
                  display: 'flex',
                  flexDirection: 'column',
                  maxHeight: '420px'
                }}>
                  <div style={{ padding: '10px 14px', borderBottom: `1px solid ${COLORS.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: COLORS.textMuted, textTransform: 'uppercase' }}>Trade Subgroup</span>
                    {selectedTradeSubgroup && (
                      <button onClick={() => { setSelectedTradeSubgroup(''); setTradeSubgroupDropdownOpen(false); }} style={{ fontSize: '11px', color: COLORS.textMuted, fontWeight: '700', background: 'none', border: 'none', cursor: 'pointer' }}>Clear</button>
                    )}
                  </div>
                  <div style={{ overflowY: 'auto', flex: 1 }}>
                    {subgroups.map(sub => (
                      <div key={sub}
                        onClick={() => {
                          setSelectedTradeSubgroup(sub);
                          setTradeSubgroupDropdownOpen(false);
                        }}
                        style={{
                          padding: '8px 14px',
                          cursor: 'pointer',
                          fontSize: '13px',
                          color: COLORS.textMain,
                          fontWeight: selectedTradeSubgroup === sub ? '700' : '500',
                          background: selectedTradeSubgroup === sub ? 'rgba(39, 84, 157, 0.06)' : 'transparent'
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(39, 84, 157, 0.06)'}
                        onMouseLeave={e => e.currentTarget.style.background = selectedTradeSubgroup === sub ? 'rgba(39, 84, 157, 0.06)' : 'transparent'}
                      >
                        {sub}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button onClick={handleCopy} style={{
              background: copied ? COLORS.green : COLORS.textMain,
              border: 'none',
              color: '#fff',
              padding: '6px 16px',
              borderRadius: '10px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontWeight: '600',
              transition: 'background 0.2s ease'
            }}>
              {copied ? <><Check size={14} /> Copied!</> : <><Copy size={14} /> Copy</>}
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
          <KPICard label="Work In Progress" value={formatCurrency(data.wip?.total || 0)} trend={`${data.wip?.job_count || 0} jobs`} color={COLORS.purple} subValue={(() => {
            const today = new Date().toISOString().slice(0, 10);
            const todayWip = (data.wip?.by_day || []).find(d => d.date === today);
            return todayWip ? `Today: ${formatCurrency(todayWip.value)}` : 'Today: £0';
          })()} />
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
                      <span style={{ fontSize: '22px', fontWeight: '800', color: COLORS.purple, letterSpacing: '-0.5px' }}>{data.sales?.today || '£0'}</span>
                    </div>
                  </div>
                  <div className="toggle-group">
                    <button className={`toggle-btn ${salesView === 'monthly' ? 'active' : ''}`} onClick={() => setSalesView('monthly')}>Monthly</button>
                    <button className={`toggle-btn ${salesView === 'quarterly' ? 'active' : ''}`} onClick={() => setSalesView('quarterly')}>Quarterly</button>
                  </div>
                </div>
                <ReactECharts option={getSalesOption({ salesView, data })} theme={theme} onEvents={{ 'click': (p) => { setSelectedPoint(p); setSidePanelOpen(true); } }} style={{ height: '450px' }} />
                <InsightCapsule content={insights.sales} />
              </div>
              {!collFlipped && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
                  {(() => {
                    const monthly = data.sales?.monthly || [];
                    const cur = monthly[monthly.length - 1];
                    const mtdSales = cur?.sales || 0;
                    const monthTarget = cur?.target || 0;
                    const remaining = Math.max(0, monthTarget - mtdSales);
                    const pct = monthTarget > 0 ? Math.min(100, Math.round((mtdSales / monthTarget) * 100)) : 0;
                    return (
                      <div className="chart-card" style={{ padding: '14px 20px', flexShrink: 0, flexGrow: 0, minHeight: 'auto' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                          <div style={{ fontSize: '26px', fontWeight: '900', color: remaining > 0 ? COLORS.purple : '#10b981' }}>{formatCurrency(remaining)}</div>
                          <div style={{ fontSize: '16px', fontWeight: '800', color: remaining > 0 ? COLORS.textMain : '#10b981' }}>{remaining > 0 ? 'to reach target' : 'Target reached!'}</div>
                        </div>
                        <div style={{ background: '#f1f5f9', borderRadius: '6px', height: '8px', overflow: 'hidden', marginBottom: '8px' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: pct >= 100 ? '#10b981' : COLORS.purple, borderRadius: '6px', transition: 'width 0.6s ease' }} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: COLORS.textDim }}>
                          <span>MTD: {formatCurrency(mtdSales)} ({pct}%)</span>
                          <span>Target: {formatCurrency(monthTarget)}</span>
                        </div>
                      </div>
                    );
                  })()}
                  <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                    <div className="card-header">
                      <div className="card-title" style={{ fontSize: '13px', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Collections on Invoiced</div>
                      <button onClick={() => setCollFlipped(true)} style={{ fontSize: '11px', fontWeight: '600', color: COLORS.purple, background: 'none', border: `1px solid ${COLORS.purple}`, borderRadius: '6px', padding: '4px 10px', cursor: 'pointer', letterSpacing: '0.02em' }}>View Details</button>
                    </div>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '6px' }}>
                      <ReactECharts option={getCollectionsProgressOption({ data })} theme={theme} style={{ height: '200px', width: '100%' }} />
                      <div style={{ textAlign: 'center', marginTop: '4px' }}>
                        <div style={{ fontSize: '22px', fontWeight: '900', color: COLORS.textMain }}>{formatCurrency(data.coll?.total || 0)}</div>
                        <div style={{ fontSize: '11px', color: COLORS.textMuted }}>Current Revenue: <span
                          style={{ fontWeight: '700', borderBottom: `1px dashed ${COLORS.textDim}`, cursor: 'default' }}
                          title={`This month invoiced (${formatCurrency(data.sum?.net_billed_raw || 0)}) − Credits on this month's invoices (${formatCurrency(data.sum?.total_credit?.credits_this_invoice || 0)})`}
                        >{data.sum?.current_revenue_raw != null ? formatCurrency(data.sum.current_revenue_raw) : (data.sum?.net_sales?.value || '£0')}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Collections modal overlay — regional gauges */}
            {collFlipped && (() => {
              const regionData = data.coll?.by_region || [];
              const tradeGroups = data.coll?.by_trade_group || [];
              const cells = regionData.length > 0 ? regionData : tradeGroups;
              const gridCols = cells.length <= 2 ? `repeat(2, 1fr)` : `repeat(3, 1fr)`;
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
                    width: cells.length <= 2 ? 'min(800px, 92vw)' : 'min(1300px, 96vw)',
                    maxHeight: '92vh',
                    overflowY: 'auto',
                    animation: 'collModalFlip 0.5s cubic-bezier(0.4,0.2,0.2,1) both',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.28)',
                  }}>
                    <div className="card-header">
                      <div style={{ fontSize: '13px', fontWeight: '700', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Collections on Invoiced {regionData.length > 0 ? '— by Region' : ''}</div>
                      <button onClick={() => setCollFlipped(false)} style={{ fontSize: '11px', fontWeight: '600', color: COLORS.slate, background: '#fff', border: `1px solid ${COLORS.border}`, borderRadius: '6px', padding: '5px 14px', cursor: 'pointer' }}>✕ Close</button>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: gridCols, gap: '8px', padding: '8px 8px 4px' }}>
                      {cells.map((g, i) => {
                        const color = REGION_COLORS[g.name] || TRADE_GAUGE_COLORS[i % TRADE_GAUGE_COLORS.length];
                        return (
                          <div key={g.name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4px 12px 8px' }}>
                            <ReactECharts
                              option={getTradeGaugeOption(g.collected, g.invoiced || g.collected, color)}
                              theme={theme}
                              style={{ height: '210px', width: '100%' }}
                            />
                            <div style={{ textAlign: 'center', marginTop: '-8px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                              <div style={{ fontSize: '12px', fontWeight: '700', color: COLORS.textMain, lineHeight: 1.3 }}>{g.name}</div>
                              <div style={{ fontSize: '14px', fontWeight: '900', color: COLORS.textMain, marginTop: '2px' }}>{formatCurrency(g.collected)}</div>
                              <div style={{ fontSize: '10px', color: COLORS.textDim, marginTop: '1px' }}>of {formatCurrency(g.invoiced)}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })()}

            <div className="split-grid" style={{ gridTemplateColumns: '3.5fr 6.5fr', alignItems: 'stretch' }}>
              {(() => {
                const now = new Date();
                const tradeDate = new Date(now.getFullYear(), now.getMonth() - tradeMonthOffset, 1);
                const tradeMonthKey = `${tradeDate.getFullYear()}-${String(tradeDate.getMonth() + 1).padStart(2, '0')}`;
                const tradeMonthLabel = tradeDate.toLocaleDateString('en-GB', { month: 'short', year: '2-digit' });
                return (
                  <div className="chart-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div className="card-title">Sales Breakdown by Region</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '2px', fontSize: '12px', fontWeight: '700', color: COLORS.textMain, background: COLORS.cardBg, border: `1px solid ${COLORS.border}`, borderRadius: '8px', padding: '4px 4px' }}>
                        <button onClick={() => setTradeMonthOffset(o => Math.min(o + 1, 13))} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', color: COLORS.textMuted, padding: '2px 8px', borderRadius: '6px', transition: 'background 0.15s' }} onMouseEnter={e => e.target.style.background = '#f1f5f9'} onMouseLeave={e => e.target.style.background = 'none'}>&lt;</button>
                        <span style={{ minWidth: '56px', textAlign: 'center', color: COLORS.textMain }}>{tradeMonthLabel}</span>
                        <button onClick={() => setTradeMonthOffset(o => Math.max(o - 1, 0))} disabled={tradeMonthOffset === 0} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', color: tradeMonthOffset === 0 ? COLORS.border : COLORS.textMuted, padding: '2px 8px', borderRadius: '6px', transition: 'background 0.15s' }} onMouseEnter={e => { if (tradeMonthOffset > 0) e.target.style.background = '#f1f5f9' }} onMouseLeave={e => e.target.style.background = 'none'}>&gt;</button>
                      </div>
                    </div>
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
                      {getByRegionOption({ data, tradeMonthKey: tradeMonthOffset > 0 ? tradeMonthKey : null }) ? (
                        <ReactECharts
                          option={getByRegionOption({ data, tradeMonthKey: tradeMonthOffset > 0 ? tradeMonthKey : null })}
                          theme={theme}
                          style={{ height: '100%', minHeight: '300px', width: '100%' }}
                        />
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px', color: COLORS.textMuted }}>No regional data</div>
                      )}
                    </div>
                  </div>
                );
              })()}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="chart-card" style={{ minHeight: 'auto' }}>
                  <div className="card-header"><div className="card-title">Daily Target</div></div>
                  <ReactECharts option={getDailyTargetOption({ data })} theme={theme} style={{ height: '360px' }} />
                  {insights.daily_target && <InsightCapsule content={insights.daily_target} />}
                </div>
              </div>
            </div>
          </section>

          <section className="dashboard-section">
            <h2 className="section-title-main"><TrendingUp size={32} /> Average Job Value</h2>
            <div style={{ display: 'grid', gridTemplateColumns: (data.out?.ajv_regional || []).length > 0 ? '1fr 1fr' : '1fr', gap: '16px', alignItems: 'stretch' }}>
              <div className="chart-card">
                <div className="card-header"><div className="card-title">Overall AJV Trend</div></div>
                <ReactECharts option={getAJVOption({ data })} theme={theme} style={{ height: '320px' }} />
              </div>
              {getRegionalAJVOption({ data }) && (
                <div className="chart-card">
                  <div className="card-header"><div className="card-title">Regional AJV Trend</div></div>
                  <ReactECharts option={getRegionalAJVOption({ data })} theme={theme} style={{ height: '320px' }} />
                </div>
              )}
            </div>
          </section>

          <section className="dashboard-section">
            <h2 className="section-title-main"><Briefcase size={32} /> Operational Insights</h2>
            <div className="ops-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title">{donutDrill ? `${donutDrill} — Jobs by Region` : 'Job Type Distribution'}</div>
                  {donutDrill ? <button className="back-button" onClick={() => setDonutDrill(null)}><ArrowLeft size={14} /> Back</button> : <span style={{ fontSize: '11px', color: COLORS.textMuted, fontWeight: '600' }}>Click to view details</span>}
                </div>
                {donutDrill ? (
                  <ReactECharts option={getJobTypeRegionalCountsOption({ data, donutDrill })} theme={theme} style={{ height: '320px' }} />
                ) : (
                  <ReactECharts option={getJobTypeOption({ data, donutDrill: null })} theme={theme} style={{ height: '320px' }} onEvents={{ 'click': (p) => setDonutDrill(p.name) }} />
                )}
              </div>
              <div className="chart-card">
                <div className="card-header">
                  <div className="card-title">{revenueDrill ? `${revenueDrill} — Revenue by Region` : 'Job Type Revenue'}</div>
                  {revenueDrill ? <button className="back-button" onClick={() => setRevenueDrill(null)}><ArrowLeft size={14} /> Back</button> : <span style={{ fontSize: '11px', color: COLORS.textMuted, fontWeight: '600' }}>Click to view details</span>}
                </div>
                {revenueDrill ? (
                  <ReactECharts option={getJobTypeRegionalRevenueOption({ data, revenueDrill })} theme={theme} style={{ height: '320px' }} />
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
            {insights.review_rating && <BigInsight content={insights.review_rating} />}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '12px' }}>
              <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', minHeight: 'auto' }}>
                <div className="card-header">
                  <div className="card-title">Work in Progress</div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '28px', fontWeight: '800', color: COLORS.textMain, letterSpacing: '-0.5px' }}>
                      {formatCurrency(data.wip?.total || 0)}
                    </div>
                    <div style={{ fontSize: '12px', color: COLORS.textMuted }}>
                      {data.wip?.job_count || 0} jobs
                    </div>
                  </div>
                </div>
                <ReactECharts style={{ height: '340px', flex: 1 }} theme={theme} option={(() => {
                  const today = new Date().toISOString().slice(0, 10);
                  const filtered = (data.wip?.by_day || []).filter(d => d.date >= today);
                  return {
                    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].axisValueLabel}<br/>${p[0].marker} ${formatCurrency(p[0].value)} (${p[0].data.jobs} jobs)` },
                    grid: { left: '3%', right: '4%', bottom: '8%', top: '12%', containLabel: true },
                    xAxis: { type: 'category', data: filtered.map(d => { const dt = new Date(d.date); return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }); }), axisLabel: { fontSize: 11, color: COLORS.textMuted } },
                    yAxis: { type: 'value', axisLabel: { fontSize: 11, color: COLORS.textMuted, formatter: v => `£${(v / 1000).toFixed(0)}k` }, splitLine: { lineStyle: { color: COLORS.border, type: 'dashed', opacity: 0.3 } } },
                    series: [{ type: 'bar', data: filtered.map(d => ({ value: Math.round(d.value), jobs: d.jobs })), itemStyle: { color: COLORS.purple, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 40, label: { show: true, position: 'top', fontSize: 11, fontWeight: '600', color: COLORS.slate, formatter: p => `£${(p.value / 1000).toFixed(1)}k` } }]
                  };
                })()} />
              </div>
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
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="chart-card">
                <div className="card-header"><div className="card-title">Outstanding by Account Type</div><span style={{ fontSize: '11px', color: COLORS.textMuted, fontWeight: '600' }}>Click to view details</span></div>
                <ReactECharts option={getAgingOption({ data })} theme={theme} style={{ height: '350px' }} onEvents={{ 'click': (p) => { setAgingDrillType(p.name); setAgingDrillRegion(p.seriesName || null); } }} />
              </div>
              <div className="chart-card">
                <div className="card-header"><div className="card-title">Aged Debt by Days</div><span style={{ fontSize: '11px', color: COLORS.textMuted, fontWeight: '600' }}>Click to view details</span></div>
                <ReactECharts option={(() => {
                  const regional = data.out?.aging_regional || {};
                  const regions = regional.regions || [];
                  const bucketsByRegion = regional.buckets || {};
                  const bucketKeys = ['<30 Days', '30-60 Days', '60-90 Days', '>90 Days'];
                  const bucketLabels = ['< 30 Days', '30–60 Days', '60–90 Days', '> 90 Days'];

                  if (regions.length > 0 && Object.keys(bucketsByRegion).length > 0) {
                    return {
                      tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>` + p.map(d => `${d.marker} ${d.seriesName}: <b>${formatCurrency(d.value)}</b>`).join('<br/>') },
                      legend: { data: regions, top: 0, right: 0, textStyle: { fontSize: 11, fontWeight: '600', color: COLORS.textMain } },
                      grid: { left: '3%', right: '12%', bottom: '5%', top: '12%', containLabel: true },
                      xAxis: { type: 'value', show: false },
                      yAxis: { type: 'category', data: bucketLabels, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
                      series: regions.map(r => ({
                        name: r,
                        type: 'bar',
                        data: bucketKeys.map(k => bucketsByRegion[r]?.[k] || 0),
                        itemStyle: { color: REGION_COLORS[r] || COLORS.purpleLight },
                        label: { show: true, position: 'right', formatter: p => formatCurrency(p.value), fontWeight: '900', fontSize: 11, color: COLORS.textMain }
                      }))
                    };
                  }

                  // Fallback
                  const b = data.out?.aging?.buckets || {};
                  const categories = ['< 30 Days', '30–60 Days', '60–90 Days', '> 90 Days'];
                  const values = [b['<30 Days'] || 0, b['30-60 Days'] || 0, b['60-90 Days'] || 0, (b['90-120 Days'] || 0) + (b['>120 Days'] || 0)];
                  return {
                    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>${p[0].marker} ${formatCurrency(p[0].value)}` },
                    grid: { left: '3%', right: '10%', bottom: '5%', top: '5%', containLabel: true },
                    xAxis: { type: 'value', show: false },
                    yAxis: { type: 'category', data: categories, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: COLORS.textMain, fontWeight: 'bold' } },
                    series: [{ type: 'bar', data: values, itemStyle: { color: COLORS.purpleLight, borderRadius: 0 }, barWidth: '50%', label: { show: true, position: 'right', formatter: p => formatCurrency(p.value), fontWeight: '900', fontSize: 11, color: COLORS.textMain } }]
                  };
                })()} theme={theme} style={{ height: '350px' }} onEvents={{ 'click': (p) => { setAgingDrillType(p.name); setAgingDrillRegion(p.seriesName || null); } }} />
              </div>
            </div>
            <div className="chart-card" style={{ marginTop: '16px', minHeight: 'auto' }}>
              <div className="card-header"><div className="card-title">Rolling Collections (14m)</div></div>
              <ReactECharts option={getCollectionsTrendOption({ data })} theme={theme} style={{ height: '380px' }} />
            </div>

            {/* Aging drill-down modal */}
            {agingDrillType && (() => {
              const bucketKeyMap = { '< 30 Days': '<30 Days', '30–60 Days': '30-60 Days', '60–90 Days': '60-90 Days', '> 90 Days': null };
              const mappedKey = bucketKeyMap[agingDrillType];
              let invoices;
              if (mappedKey !== undefined) {
                if (mappedKey) {
                  invoices = data.out?.aging?.bucket_invoices?.[mappedKey] || [];
                } else {
                  invoices = [...(data.out?.aging?.bucket_invoices?.['90-120 Days'] || []), ...(data.out?.aging?.bucket_invoices?.['>120 Days'] || [])].sort((a, b) => b.outstanding - a.outstanding);
                }
              } else {
                invoices = data.out?.aging?.invoices?.[agingDrillType] || [];
              }
              // Filter by region if clicked on a regional bar
              if (agingDrillRegion) {
                invoices = invoices.filter(inv => inv.region === agingDrillRegion);
              }
              return (
                <div
                  onClick={(e) => { if (e.target === e.currentTarget) { setAgingDrillType(null); setAgingDrillRegion(null); } }}
                  style={{
                    position: 'fixed', inset: 0, zIndex: 1000,
                    background: 'rgba(15, 23, 42, 0.45)',
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    animation: 'collBackdropIn 0.35s ease both',
                  }}
                >
                  <div style={{
                    width: 'min(1200px, 94vw)',
                    height: '80vh',
                    maxHeight: '80vh',
                    display: 'flex',
                    flexDirection: 'column',
                    animation: 'collModalFlip 0.5s cubic-bezier(0.4,0.2,0.2,1) both',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.28)',
                    overflow: 'hidden',
                    background: '#fff',
                    borderRadius: '12px',
                    padding: '12px 16px',
                    border: `1px solid ${COLORS.border}`,
                  }}>
                    <div className="card-header" style={{ background: '#fff', zIndex: 1, flexShrink: 0 }}>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        {agingDrillType}{agingDrillRegion ? ` – ${agingDrillRegion}` : ''} — {invoices.length} Outstanding Invoices ({formatCurrency(invoices.reduce((s, i) => s + i.outstanding, 0))})
                      </div>
                      <button onClick={() => { setAgingDrillType(null); setAgingDrillRegion(null); }} style={{ fontSize: '11px', fontWeight: '600', color: COLORS.slate, background: '#fff', border: `1px solid ${COLORS.border}`, borderRadius: '6px', padding: '5px 14px', cursor: 'pointer' }}>✕ Close</button>
                    </div>
                    <div style={{ overflowY: 'auto', flex: 1 }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ borderBottom: `2px solid ${COLORS.border}`, textAlign: 'left', position: 'sticky', top: 0, zIndex: 1 }}>
                            <th style={{ padding: '10px 12px', fontWeight: '700', color: COLORS.textMuted, fontSize: '11px', textTransform: 'uppercase', background: '#fff' }}>Invoice</th>
                            <th style={{ padding: '10px 12px', fontWeight: '700', color: COLORS.textMuted, fontSize: '11px', textTransform: 'uppercase', background: '#fff' }}>Account</th>
                            <th style={{ padding: '10px 12px', fontWeight: '700', color: COLORS.textMuted, fontSize: '11px', textTransform: 'uppercase', background: '#fff' }}>Date</th>
                            <th style={{ padding: '10px 12px', fontWeight: '700', color: COLORS.textMuted, fontSize: '11px', textTransform: 'uppercase', textAlign: 'right', background: '#fff' }}>Charge Net</th>
                            <th style={{ padding: '10px 12px', fontWeight: '700', color: COLORS.textMuted, fontSize: '11px', textTransform: 'uppercase', textAlign: 'right', background: '#fff' }}>Outstanding (excl. VAT)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {invoices.map((inv, idx) => (
                            <tr key={inv.name || idx} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
                              <td style={{ padding: '9px 12px', fontWeight: '600' }}>{inv.id ? <a href={`https://chumley.lightning.force.com/lightning/r/Customer_Invoice__c/${inv.id}/view`} target="_blank" rel="noopener noreferrer" style={{ color: COLORS.purple, textDecoration: 'none' }} onMouseEnter={e => e.target.style.textDecoration = 'underline'} onMouseLeave={e => e.target.style.textDecoration = 'none'}>{inv.name}</a> : inv.name}</td>
                              <td style={{ padding: '9px 12px', color: COLORS.textMain }}>{inv.account_name}</td>
                              <td style={{ padding: '9px 12px', color: COLORS.textDim }}>{inv.date}</td>
                              <td style={{ padding: '9px 12px', textAlign: 'right', color: COLORS.textMain }}>{formatCurrency(inv.charge_net)}</td>
                              <td style={{ padding: '9px 12px', textAlign: 'right', fontWeight: '700', color: COLORS.purple }}>{formatCurrency(inv.outstanding)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              );
            })()}
          </section>
        </div>
      </main>

      <div className={`side-panel ${sidePanelOpen ? 'open' : ''}`}>
        <button className="close-panel" onClick={() => setSidePanelOpen(false)}><X size={20} /></button>
        <h2 style={{ color: COLORS.textMain, fontWeight: '900', marginBottom: '8px' }}>{selectedPoint?.name} Drill-down</h2>
        <p style={{ color: COLORS.textMuted, marginBottom: '32px' }}>Details for selected period</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {data.sales.trades.slice(0, 10).map((t, idx) => (
            <div key={idx} style={{ background: '#fff', padding: '16px', borderRadius: '12px', border: `1px solid ${COLORS.border}` }}>
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

export default TradePerformance;
