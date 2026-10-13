import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Menu, ShieldCheck } from 'lucide-react';
import styles from './AppLayout.module.css';
import { Sidebar } from '../components/Sidebar/Sidebar';
import { IconButton } from '../components/IconButton/IconButton';
import { Badge } from '../components/Badge/Badge';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';

export const AppLayout: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Health check query proves backend connectivity
  const { data: healthData, isSuccess } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => apiClient.checkHealth(),
    refetchInterval: 60000,
  });

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
              <span className={styles.instName}>Metropolitan State University</span>
            </div>
          </div>

          <div className={styles.rightSection}>
            {isSuccess && healthData ? (
              <Badge
                variant="success"
                size="sm"
                icon={<ShieldCheck size={12} />}
              >
                Engine Connected
              </Badge>
            ) : (
              <Badge variant="neutral" size="sm">
                Connecting...
              </Badge>
            )}

            <div className={styles.userProfile}>
              <div className={styles.userAvatar}>EV</div>
              <div className={styles.userInfo}>
                <span className={styles.userName}>Dr. E. Vance</span>
                <span className={styles.userRole}>Faculty Advisor</span>
              </div>
            </div>
          </div>
        </header>

        {/* Dynamic Content View */}
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
};
