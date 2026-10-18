import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';

export const AppShell: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebarWidth = collapsed ? '64px' : '240px';

  return (
    <div className="min-h-screen bg-[#0a0d14] forensic-grid">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <div
        className="flex flex-col min-h-screen transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <TopBar
          sidebarCollapsed={collapsed}
          onMobileMenuOpen={() => setMobileOpen(true)}
        />

        {/* Page content */}
        <main className="flex-1 mt-14 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
