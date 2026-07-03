import React, { useState } from 'react';
import { createPortal } from 'react-dom';

interface ImageGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (searchQuery: string, useAi: boolean) => void;
  defaultSearchQuery: string;
}

export default function ImageGenerationModal({ isOpen, onClose, onGenerate, defaultSearchQuery }: ImageGenerationModalProps) {
  const [searchQuery, setSearchQuery] = useState(defaultSearchQuery);
  const [useAi, setUseAi] = useState(false); // Default to Pexels

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      alert('Search phrase cannot be empty!');
      return;
    }
    onGenerate(searchQuery.trim(), useAi);
    onClose(); // Close modal after generating
  };

  return createPortal(
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.7)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10001
    }}>
      <div className="ds-scale-in" style={{
        backgroundColor: 'var(--surface)',
        padding: '32px',
        borderRadius: 'var(--r-2xl)',
        boxShadow: 'var(--shadow-xl)',
        border: '1px solid var(--border)',
        width: '90%',
        maxWidth: '500px',
        color: 'var(--text)'
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '24px', fontSize: '24px', textAlign: 'center' }}>Generate Image</h2>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '15px' }}>
            <label htmlFor="searchQuery" style={{ display: 'block', marginBottom: '8px', fontWeight: 700, color: 'var(--text-soft)' }}>
              Search Phrase:
            </label>
            <input
              id="searchQuery"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 14px',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-md)',
                fontSize: '15px',
                background: 'var(--surface-2)',
                color: 'var(--text)',
                boxSizing: 'border-box'
              }}
              placeholder="Enter search phrase"
            />
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
              (Catalan text will be auto-translated to English for AI/Pexels)
            </p>
          </div>

          <div style={{ marginBottom: '25px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 700, color: 'var(--text-soft)' }}>
              Image Source:
            </label>
            <div style={{ display: 'flex', gap: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center' }}>
                <input
                  type="radio"
                  name="imageSource"
                  value="pexels"
                  checked={!useAi}
                  onChange={() => setUseAi(false)}
                  style={{ marginRight: '8px' }}
                />
                Pexels (Stock Photo)
              </label>
              <label style={{ display: 'flex', alignItems: 'center' }}>
                <input
                  type="radio"
                  name="imageSource"
                  value="ai"
                  checked={useAi}
                  onChange={() => setUseAi(true)}
                  style={{ marginRight: '8px' }}
                />
                AI Image Generator
              </label>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '12px 20px',
                background: 'var(--surface)',
                color: 'var(--text-soft)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                fontSize: '15px',
                fontWeight: 700
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{
                padding: '12px 22px',
                background: 'var(--brand-gradient)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                fontSize: '15px',
                fontWeight: 700,
                boxShadow: 'var(--shadow-brand)'
              }}
            >
              Generate
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
