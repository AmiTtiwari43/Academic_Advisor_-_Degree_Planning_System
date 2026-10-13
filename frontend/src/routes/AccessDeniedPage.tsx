import React from 'react';
import { Link } from 'react-router-dom';
import { Button, ErrorState } from '../components';
import styles from './NotFoundPage.module.css';

export const AccessDeniedPage: React.FC = () => {
  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <ErrorState
          title="403 — Access Denied"
          message="You do not have the required institutional authorization or role permissions to view this academic resource."
          action={
            <Link to="/dashboard">
              <Button variant="primary">Return to Dashboard</Button>
            </Link>
          }
        />
      </div>
    </div>
  );
};
