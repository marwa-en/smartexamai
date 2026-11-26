import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import Footer from './Footer';
import { useAuth } from '../context/AuthContext';

export default function Layout() {
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div data-role={user?.role}>
      <div className="app-layout">
        <Sidebar open={sidebarOpen} />
        <div className="main-content">
          <Navbar onToggleSidebar={() => setSidebarOpen((o) => !o)} />
          <div className="page fade-in">
            <Outlet />
          </div>
          <Footer />
        </div>
      </div>
    </div>
  );
}
