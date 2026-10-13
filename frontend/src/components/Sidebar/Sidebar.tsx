import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  GraduationCap,
  LayoutDashboard,
  BookOpen,
  Calendar,
  Users,
  Compass,
  FileCheck,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  X,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Role } from '../../types';
import styles from './Sidebar.module.css';
import { IconButton } from '../IconButton/IconButton';

export interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  allowedRoles?: Role[];
}

export interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

const ALL_NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Overview', icon: <LayoutDashboard size={20} /> },
  { to: '/curriculum', label: 'Curriculum Catalog', icon: <BookOpen size={20} /> },
  {
    to: '/plan',
    label: 'Degree Planner',
    icon: <Calendar size={20} />,
    allowedRoles: ['STUDENT', 'ADVISOR', 'COORDINATOR'],
  },
  {
    to: '/audit',
    label: 'Degree Audit',
    icon: <FileCheck size={20} />,
    allowedRoles: ['STUDENT', 'ADVISOR', 'COORDINATOR', 'HOD'],
  },
  {
    to: '/advising',
    label: 'Advisor Workspace',
    icon: <Users size={20} />,
    allowedRoles: ['ADVISOR', 'COORDINATOR', 'HOD', 'ADMIN'],
  },
  {
    to: '/careers',
    label: 'Career Guidance',
    icon: <Compass size={20} />,
    allowedRoles: ['STUDENT', 'ADVISOR', 'COORDINATOR'],
  },
  {
    to: '/admin',
    label: 'Institution Admin',
    icon: <ShieldCheck size={20} />,
    allowedRoles: ['ADMIN'],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onMobileClose,
}) => {
  const { activeRole } = useAuth();

  const visibleNavItems = ALL_NAV_ITEMS.filter((item) => {
    if (!item.allowedRoles) return true;
    if (!activeRole) return true; // show default if role not yet loaded
    return item.allowedRoles.includes(activeRole);
  });

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className={styles.mobileBackdrop}
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={[
          styles.sidebar,
          isCollapsed ? styles.collapsed : '',
          isMobileOpen ? styles.mobileOpen : '',
        ]
          .filter(Boolean)
          .join(' ')}
        aria-label="Primary Navigation"
      >
        {/* Brand Header */}
        <div className={styles.brandHeader}>
          <div className={styles.logoBadge}>
            <GraduationCap size={22} className={styles.brandIcon} />
          </div>
          {!isCollapsed && (
            <div className={styles.brandText}>
              <span className={styles.brandName}>Academic Advisor</span>
              <span className={styles.brandSub}>Degree Engine</span>
            </div>
          )}

          {/* Mobile Close Button */}
          <div className={styles.mobileClose}>
            <IconButton
              icon={<X size={20} />}
              aria-label="Close navigation menu"
              onClick={onMobileClose}
              size="sm"
            />
          </div>
        </div>

        {/* Navigation List */}
        <nav className={styles.nav}>
          <ul className={styles.navList}>
            {visibleNavItems.map((item) => (
              <li key={item.to} className={styles.navItem}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    [styles.navLink, isActive ? styles.activeLink : '']
                      .filter(Boolean)
                      .join(' ')
                  }
                  title={isCollapsed ? item.label : undefined}
                  onClick={onMobileClose}
                >
                  <span className={styles.icon}>{item.icon}</span>
                  {!isCollapsed && <span className={styles.label}>{item.label}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Footer with collapse toggle */}
        <div className={styles.sidebarFooter}>
          <button
            type="button"
            className={styles.collapseButton}
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            {!isCollapsed && <span>Collapse Sidebar</span>}
          </button>
        </div>
      </aside>
    </>
  );
};
