import React, { useState } from 'react';
import { Outlet, useNavigate, Navigate } from 'react-router-dom';
import { LogOut, Menu, Sparkles } from 'lucide-react';
import styles from './AppLayout.module.css';
import { Sidebar } from '../components/Sidebar/Sidebar';
import { IconButton } from '../components/IconButton/IconButton';
import { NotificationBell } from '../components/Notifications';
import { AssistantDrawer } from '../components/Assistant';
import { useAuth } from '../context/AuthContext';

export const AppLayout: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const { user, activeMembership, activeRole, logout, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Guard: If authentication state is loading, wait before mounting children
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#F8F9FC',
        color: '#0B1324',
        fontFamily: 'Inter, sans-serif'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '3px solid #E2E8F0',
            borderTopColor: '#0E7577',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite'
          }} />
          <span style={{ fontSize: '14px', fontWeight: 500, color: '#475569' }}>
            Verifying institutional session...
          </span>
        </div>
      </div>
    );
  }

  // Guard: If not authenticated, redirect to login page immediately
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const displayName =
    user?.preferred_name ||
    (user?.first_name ? `${user.first_name} ${user.last_name}` : user?.username) ||
    'Authenticated User';

  const userInitials = user?.first_name
    ? `${user.first_name[0]}${user.last_name ? user.last_name[0] : ''}`.toUpperCase()
    : (user?.username ? user.username.slice(0, 2).toUpperCase() : 'AU');

  return (
    <div className={styles.appShell}>
      {/* Primary Sidebar */}
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        isMobileOpen={isMobileOpen}
        onMobileClose={() => setIsMobileOpen(false)}
      />

      {/* Main Container */}
      <div className={styles.mainContainer}>
        {/* Top Header */}
        <header className={styles.topBar}>
          <div className={styles.leftSection}>
            <div className={styles.mobileMenuButton}>
              <IconButton
                icon={<Menu size={22} />}
                aria-label="Open mobile menu"
                onClick={() => setIsMobileOpen(true)}
              />
            </div>
            <div className={styles.institutionContext}>
              <span className={styles.instLabel}>Active Institution</span>
              <span className={styles.instName}>
                {activeMembership?.institution_name || 'Metropolitan State University'}
              </span>
            </div>
          </div>

          <div className={styles.rightSection}>
            <button
              type="button"
              className={styles.assistantButton}
              onClick={() => setIsAssistantOpen(true)}
              aria-label="Open AI Advisor Assistant"
            >
              <Sparkles size={14} />
              <span>AI Advisor</span>
            </button>

            <NotificationBell />

            <div className={styles.userProfile}>
              <div className={styles.userAvatar}>{userInitials}</div>
              <div className={styles.userInfo}>
                <span className={styles.userName}>{displayName}</span>
                <span className={styles.userRole}>
                  {activeRole ? activeRole.replace('_', ' ') : 'Academic Portal'}
                </span>
              </div>
            </div>

            <IconButton
              icon={<LogOut size={18} />}
              aria-label="Sign out"
              onClick={handleLogout}
              size="sm"
            />
          </div>
        </header>

        {/* Dynamic Content View */}
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>

      {/* AI Assistant Drawer */}
      <AssistantDrawer
        isOpen={isAssistantOpen}
        onClose={() => setIsAssistantOpen(false)}
      />
    </div>
  );
};
