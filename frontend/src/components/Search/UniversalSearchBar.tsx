import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, User, GraduationCap, BookOpen, Layers, FileText, ArrowRight, Loader2 } from 'lucide-react';
import { searchApi, GlobalSearchResults } from '../../api/search';
import styles from './UniversalSearchBar.module.css';

export const UniversalSearchBar: React.FC = () => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<GlobalSearchResults | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Global Ctrl+K / '/' shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await searchApi.search(query.trim());
        setResults(res);
      } catch {
        // Fallback gracefully on search error
      } finally {
        setIsLoading(false);
      }
    }, 180);

    return () => clearTimeout(timer);
  }, [query, isOpen]);

  const handleSelectStudent = (studentId: string) => {
    setIsOpen(false);
    navigate(`/plan?studentId=${studentId}`);
  };

  const handleSelectCourse = () => {
    setIsOpen(false);
    navigate('/curriculum');
  };

  const handleSelectProgramme = () => {
    setIsOpen(false);
    navigate('/curriculum');
  };

  const handleSelectPlan = () => {
    setIsOpen(false);
    navigate('/advising');
  };

  const totalResults =
    (results?.students.length || 0) +
    (results?.faculty.length || 0) +
    (results?.courses.length || 0) +
    (results?.programmes.length || 0) +
    (results?.plans.length || 0);

  return (
    <div className={styles.universalContainer} ref={containerRef}>
      <div className={styles.inputWrapper}>
        <Search size={16} className={styles.searchIcon} />
        <input
          ref={inputRef}
          type="text"
          className={styles.searchInput}
          placeholder="Search students (Reg No / Name), faculty, courses, plans..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          aria-label="Universal system search"
          data-testid="universal-search-input"
        />
        {query && (
          <button
            type="button"
            className={styles.clearButton}
            onClick={() => {
              setQuery('');
              inputRef.current?.focus();
            }}
            aria-label="Clear universal search"
          >
            <X size={14} />
          </button>
        )}
        <div className={styles.shortcutHint} title="Press Ctrl+K to search">
          <span>Ctrl</span>
          <span>K</span>
        </div>
      </div>

      {/* Floating Dropdown Results */}
      {isOpen && (
        <div className={styles.dropdownPalette} role="listbox">
          {isLoading ? (
            <div className={styles.loadingSpinner}>
              <Loader2 size={24} className="animate-spin" />
            </div>
          ) : totalResults === 0 && query ? (
            <div className={styles.emptyState}>
              No records found matching &ldquo;{query}&rdquo;. Try a registration number, student name, or course code.
            </div>
          ) : (
            <>
              {/* Students Section */}
              {results && results.students.length > 0 && (
                <div>
                  <div className={styles.sectionHeader}>
                    <span>Students ({results.students.length})</span>
                    <GraduationCap size={13} />
                  </div>
                  {results.students.map((s) => (
                    <div
                      key={s.id}
                      className={styles.resultItem}
                      onClick={() => handleSelectStudent(s.id)}
                      role="option"
                      aria-selected={false}
                    >
                      <div className={styles.itemMain}>
                        <div className={styles.itemTitleRow}>
                          <span className={styles.itemTitle}>{s.name}</span>
                          <span className={styles.regNoBadge}>{s.registration_number}</span>
                        </div>
                        <span className={styles.itemSubtext}>
                          {s.programme_code} &bull; @{s.username} &bull; {s.email}
                        </span>
                      </div>
                      <div className={styles.itemMeta}>
                        <span>CGPA: {s.cgpa}</span>
                        <ArrowRight size={14} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Faculty & Advisors Section */}
              {results && results.faculty.length > 0 && (
                <div>
                  <div className={styles.sectionHeader}>
                    <span>Faculty & Advisors ({results.faculty.length})</span>
                    <User size={13} />
                  </div>
                  {results.faculty.map((f) => (
                    <div
                      key={f.id}
                      className={styles.resultItem}
                      onClick={() => {
                        setIsOpen(false);
                        navigate('/advising');
                      }}
                      role="option"
                      aria-selected={false}
                    >
                      <div className={styles.itemMain}>
                        <div className={styles.itemTitleRow}>
                          <span className={styles.itemTitle}>{f.name}</span>
                          <span className={styles.facultyBadge}>{f.registration_number}</span>
                          <span className={styles.regNoBadge}>{f.role}</span>
                        </div>
                        <span className={styles.itemSubtext}>@{f.username} &bull; {f.email}</span>
                      </div>
                      <div className={styles.itemMeta}>
                        <ArrowRight size={14} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Courses Section */}
              {results && results.courses.length > 0 && (
                <div>
                  <div className={styles.sectionHeader}>
                    <span>Courses ({results.courses.length})</span>
                    <BookOpen size={13} />
                  </div>
                  {results.courses.map((c) => (
                    <div
                      key={c.id}
                      className={styles.resultItem}
                      onClick={handleSelectCourse}
                      role="option"
                      aria-selected={false}
                    >
                      <div className={styles.itemMain}>
                        <div className={styles.itemTitleRow}>
                          <span className={styles.itemTitle}>{c.code}</span>
                          <span>{c.title}</span>
                        </div>
                        <span className={styles.itemSubtext}>{c.credits} Credits</span>
                      </div>
                      <div className={styles.itemMeta}>
                        <ArrowRight size={14} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Programmes Section */}
              {results && results.programmes.length > 0 && (
                <div>
                  <div className={styles.sectionHeader}>
                    <span>Degree Programmes ({results.programmes.length})</span>
                    <Layers size={13} />
                  </div>
                  {results.programmes.map((p) => (
                    <div
                      key={p.id}
                      className={styles.resultItem}
                      onClick={handleSelectProgramme}
                      role="option"
                      aria-selected={false}
                    >
                      <div className={styles.itemMain}>
                        <div className={styles.itemTitleRow}>
                          <span className={styles.itemTitle}>{p.code}</span>
                          <span>{p.name}</span>
                        </div>
                        <span className={styles.itemSubtext}>{p.degree_type}</span>
                      </div>
                      <div className={styles.itemMeta}>
                        <ArrowRight size={14} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Degree Plans Section */}
              {results && results.plans.length > 0 && (
                <div>
                  <div className={styles.sectionHeader}>
                    <span>Degree Plans ({results.plans.length})</span>
                    <FileText size={13} />
                  </div>
                  {results.plans.map((pl) => (
                    <div
                      key={pl.id}
                      className={styles.resultItem}
                      onClick={handleSelectPlan}
                      role="option"
                      aria-selected={false}
                    >
                      <div className={styles.itemMain}>
                        <div className={styles.itemTitleRow}>
                          <span className={styles.itemTitle}>{pl.name}</span>
                          <span className={styles.regNoBadge}>{pl.student_registration_number}</span>
                        </div>
                        <span className={styles.itemSubtext}>
                          Student: {pl.student_name} ({pl.programme_code})
                        </span>
                      </div>
                      <div className={styles.itemMeta}>
                        <span>{pl.status}</span>
                        <ArrowRight size={14} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
