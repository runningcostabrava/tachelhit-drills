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
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10001
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '30px',
        borderRadius: '12px',
        boxShadow: '0 5px 15px rgba(0,0,0,0.3)',
        width: '90%',
        maxWidth: '500px',
        color: '#333'
      }}>
        <h2 style={{ marginTop: 0, marginBottom: '20px', fontSize: '24px', textAlign: 'center' }}>Generate Image</h2>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '15px' }}>
            <label htmlFor="searchQuery" style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
              Search Phrase:
            </label>
            <input
              id="searchQuery"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ccc',
                borderRadius: '8px',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
              placeholder="Enter search phrase"
            />
            <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
              (Catalan text will be auto-translated to English for AI/Pexels)
            </p>
          </div>

          <div style={{ marginBottom: '25px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
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
                padding: '10px 20px',
                background: '#ccc',
                color: '#333',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 600
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{
                padding: '10px 20px',
                background: '#667eea',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 600
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
