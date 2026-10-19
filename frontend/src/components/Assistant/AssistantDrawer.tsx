import React, { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Sparkles,
  X,
  Send,
  ShieldAlert,
  BookOpen,
  ArrowRight,
  Info,
} from 'lucide-react';
import { assistantApi, AssistantCitation, AssistantResponse } from '../../api/assistant';
import { Badge } from '../Badge/Badge';
import styles from './AssistantDrawer.module.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  citations?: AssistantCitation[];
  groundedSummary?: string;
}

interface AssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  studentRecordId?: string;
}

const DEFAULT_SUGGESTIONS = [
  'Can I take CS201 next semester?',
  'How many remaining credits do I need to graduate?',
  'Am I eligible for CS301?',
  'What courses are available in my degree curriculum?',
];

export const AssistantDrawer: React.FC<AssistantDrawerProps> = ({
  isOpen,
  onClose,
  studentRecordId,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Fetch capabilities
  const { data: capabilities } = useQuery({
    queryKey: ['assistant-capabilities'],
    queryFn: () => assistantApi.getCapabilities(),
    staleTime: 1000 * 60 * 30, // 30 minutes
    enabled: isOpen,
  });

  // Query mutation
  const queryMutation = useMutation({
    mutationFn: (prompt: string) =>
      assistantApi.query({
        prompt,
        student_record_id: studentRecordId,
      }),
    onSuccess: (data: AssistantResponse) => {
      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: data.answer,
        citations: data.citations,
        groundedSummary: data.grounded_context_summary,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: { detail?: string; error?: string } } };
      const errMsg: Message = {
        id: `assistant-err-${Date.now()}`,
        role: 'assistant',
        text:
          axiosErr?.response?.data?.detail ||
          axiosErr?.response?.data?.error ||
          'Unable to complete query. Please ensure you are logged in with an active institutional context.',
      };
      setMessages((prev) => [...prev, errMsg]);
    },
  });

  // Scroll to bottom on new message
  useEffect(() => {
    if (chatBottomRef.current && typeof chatBottomRef.current.scrollIntoView === 'function') {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, queryMutation.isPending]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSend = (textToSend?: string) => {
    const text = (textToSend || inputValue).trim();
    if (!text || queryMutation.isPending) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    queryMutation.mutate(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className={styles.overlay}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="assistant-drawer-title"
    >
      <div className={styles.drawer}>
        {/* Header */}
        <div className={styles.drawerHeader}>
          <div className={styles.titleArea}>
            <div className={styles.iconWrapper}>
              <Sparkles size={20} />
            </div>
            <div className={styles.headerText}>
              <h2 id="assistant-drawer-title" className={styles.drawerTitle}>
                Academic AI Advisor
              </h2>
              <span className={styles.headerSubtext}>Curriculum Rules Engine Grounded</span>
            </div>
          </div>
          <div className={styles.headerActions}>
            <Badge variant="teal" size="sm">
              20 req/min
            </Badge>
            <button
              type="button"
              className={styles.closeButton}
              onClick={onClose}
              aria-label="Close Assistant Drawer"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Disclaimer Banner */}
        <div className={styles.disclaimerBanner} role="note">
          <ShieldAlert size={16} className={styles.disclaimerIcon} />
          <span>
            {capabilities?.disclaimer ||
              "AI responses are strictly grounded in your institution's published curriculum and official degree audit records. The assistant cannot make exceptions, approve degree plans, or modify records."}
          </span>
        </div>

        {/* Chat Body */}
        <div className={styles.chatBody}>
          {messages.length === 0 ? (
            <div className={styles.welcomeCard}>
              <div className={styles.welcomeIcon}>
                <BookOpen size={24} />
              </div>
              <h3 className={styles.welcomeTitle}>Degree Planning & Curriculum Assistant</h3>
              <p className={styles.welcomeDesc}>
                Ask questions about course prerequisite chains, graduation progress, or remaining
                degree requirements. All evaluations are verified by the institutional rules engine.
              </p>
              <div className={styles.suggestionsTitle}>Suggested Inquiries</div>
              <div className={styles.suggestionChips}>
                {DEFAULT_SUGGESTIONS.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={styles.suggestionChip}
                    onClick={() => handleSend(suggestion)}
                  >
                    <span>{suggestion}</span>
                    <ArrowRight size={14} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`${styles.messageRow} ${
                  msg.role === 'user' ? styles.userMessageRow : styles.assistantMessageRow
                }`}
              >
                {msg.role === 'user' ? (
                  <div className={styles.userBubble}>{msg.text}</div>
                ) : (
                  <div className={styles.assistantBubble}>
                    <div>{msg.text}</div>

                    {/* Citations Block */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className={styles.citationsBlock}>
                        <div className={styles.citationsHeading}>
                          <Info size={12} />
                          <span>Authoritative Sources & Engine Citations</span>
                        </div>
                        <div className={styles.citationsList}>
                          {msg.citations.map((c, i) => (
                            <div key={i} className={styles.citationChip}>
                              <div className={styles.citationSource}>
                                <span className={styles.citationTag}>{c.source_type}</span>
                                <span>{c.reference}</span>
                              </div>
                              <div className={styles.citationDetails}>{c.details}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {msg.groundedSummary && (
                      <div className={styles.groundedMeta}>✓ {msg.groundedSummary}</div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}

          {queryMutation.isPending && (
            <div className={`${styles.messageRow} ${styles.assistantMessageRow}`}>
              <div className={styles.loadingBubble}>
                <div className={styles.spinner} />
                <span>Evaluating curriculum rules and degree audit status...</span>
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Footer Input */}
        <div className={styles.drawerFooter}>
          <form
            className={styles.inputForm}
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <div className={styles.inputWrapper}>
              <textarea
                ref={inputRef}
                rows={2}
                className={styles.queryInput}
                placeholder="Ask about prerequisites, degree progress, courses..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={queryMutation.isPending}
                aria-label="Assistant prompt input"
              />
              <button
                type="submit"
                className={styles.sendButton}
                disabled={!inputValue.trim() || queryMutation.isPending}
                aria-label="Send query"
              >
                <Send size={16} />
              </button>
            </div>
            <div className={styles.inputFooterText}>
              <span>Enter to send · Shift+Enter for newline</span>
              <span>Zero client-side rule overrides</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
