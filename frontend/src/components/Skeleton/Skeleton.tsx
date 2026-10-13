import React from 'react';
import styles from './Skeleton.module.css';

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  variant?: 'text' | 'rect' | 'circle';
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height,
  borderRadius,
  variant = 'text',
  className = '',
}) => {
  const inlineStyle: React.CSSProperties = {
    width: width !== undefined ? (typeof width === 'number' ? `${width}px` : width) : undefined,
    height: height !== undefined ? (typeof height === 'number' ? `${height}px` : height) : undefined,
    borderRadius:
      borderRadius !== undefined
        ? typeof borderRadius === 'number'
          ? `${borderRadius}px`
          : borderRadius
        : undefined,
  };

  return (
    <div
      className={`${styles.skeleton} ${styles[variant]} ${className}`}
      style={inlineStyle}
      aria-hidden="true"
    />
  );
};
