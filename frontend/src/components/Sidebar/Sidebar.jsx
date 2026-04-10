import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Home, BarChart2, Layers, UserCircle, LogOut } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/sectorperformance', label: 'Sector Performance', icon: BarChart2 },
  { path: '/tradeperformance', label: 'Trade Performance', icon: Layers },
];

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img src="/business-performance/Aspect_Logo.svg" alt="Aspect Logo" style={{ height: '28px' }} />
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
          <button
            key={path}
            className={`sidebar-item${location.pathname === path ? ' active' : ''}`}
            onClick={() => navigate(path)}
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
};

export default Sidebar;
