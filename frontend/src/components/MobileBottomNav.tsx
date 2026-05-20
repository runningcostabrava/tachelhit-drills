import { useNavigate, useLocation } from 'react-router-dom';

interface MobileBottomNavProps {
  // No longer need onViewTests/onViewShorts as we'll use useNavigate directly
}

export default function MobileBottomNav({}: MobileBottomNavProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      height: '60px', // Adjust height as needed
      backgroundColor: 'white',
      borderTop: '1px solid #e0e0e0',
      display: 'flex',
      justifyContent: 'space-around',
      alignItems: 'center',
      boxShadow: '0 -2px 8px rgba(0,0,0,0.1)',
      zIndex: 1000
    }}>
      <button
        onClick={() => navigate('/')}
        style={{
          flex: 1,
          padding: '8px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '2px',
          color: isActive('/') ? '#667eea' : '#666',
          fontWeight: isActive('/') ? 700 : 500,
          fontSize: '11px',
        }}
      >
        <span style={{ fontSize: '20px' }}>📚</span>
        <span>Drills</span>
      </button>
      <button
        onClick={() => navigate('/tests')}
        style={{
          flex: 1,
          padding: '8px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '2px',
          color: isActive('/tests') ? '#667eea' : '#666',
          fontWeight: isActive('/tests') ? 700 : 500,
          fontSize: '11px',
        }}
      >
        <span style={{ fontSize: '20px' }}>📊</span>
        <span>Practica</span>
      </button>
      <button
        onClick={() => navigate('/library')}
        style={{
          flex: 1,
          padding: '8px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '2px',
          color: isActive('/library') ? '#667eea' : '#666',
          fontWeight: isActive('/library') ? 700 : 500,
          fontSize: '11px',
        }}
      >
        <span style={{ fontSize: '20px' }}>🎥</span>
        <span>Library</span>
      </button>
    </div>
  );
}
