import React, { useState } from 'react';
import styles from './Tabs.module.css';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab?: string;
  onChange?: (id: string) => void;
  children?: React.ReactNode;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab: controlledActiveTab,
  onChange,
  children,
  className = '',
}) => {
  const [internalActiveTab, setInternalActiveTab] = useState(tabs[0]?.id || '');
  const activeTab = controlledActiveTab !== undefined ? controlledActiveTab : internalActiveTab;

  const handleTabClick = (id: string, disabled?: boolean) => {
    if (disabled) return;
    if (controlledActiveTab === undefined) {
      setInternalActiveTab(id);
    }
    onChange?.(id);
  };

  return (
    <div className={`${styles.tabsContainer} ${className}`}>
      <div className={styles.tabList} role="tablist">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              id={`tab-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              disabled={tab.disabled}
              className={`${styles.tab} ${isActive ? styles.active : ''}`}
              onClick={() => handleTabClick(tab.id, tab.disabled)}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className={styles.counter}>{tab.count}</span>
              )}
            </button>
          );
        })}
      </div>
      {children && <div className={styles.tabPanels}>{children}</div>}
    </div>
  );
};
