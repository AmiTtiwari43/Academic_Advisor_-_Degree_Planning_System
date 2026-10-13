import React from 'react';
import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';
import styles from './NotFoundPage.module.css';
import { Button } from '../components/Button/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className={styles.container}>
      <h1 className={styles.errorCode}>404</h1>
      <h2 className={styles.title}>Academic Resource Not Found</h2>
      <p className={styles.description}>
        The requested pathway or academic resource does not exist in this catalog version or has been
        relocated.
      </p>
      <Link to="/dashboard">
        <Button variant="primary" size="md" leftIcon={<Home size={16} />}>
          Return to Degree Overview
        </Button>
      </Link>
    </div>
  );
};
