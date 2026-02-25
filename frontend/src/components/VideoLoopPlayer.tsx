
// VideoLoopPlayer component for displaying demo videos - TypeScript compliant
interface VideoLoopPlayerProps {
  videoUrl: string;
  onBack: () => void;
}

export default function VideoLoopPlayer({ videoUrl, onBack }: VideoLoopPlayerProps) {
  return (
    <div style={{
      height: '100vh',
      width: '100vw',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#111',
      color: 'white',
      padding: '20px',
      boxSizing: 'border-box'
    }}>
      <div style={{ width: '100%', maxWidth: '1280px', marginBottom: '20px' }}>
        <button
          onClick={onBack}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            background: '#333',
            color: 'white',
            border: '1px solid white',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
        >
          ← Back to Dashboard
        </button>
      </div>
      <div style={{
        width: '100%',
        maxWidth: '1280px',
        aspectRatio: '16 / 9',
        background: '#000'
      }}>
        <video
          key={videoUrl} // Use key to force re-render if URL changes
          src={videoUrl}
          autoPlay
          loop
          controls
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '8px'
          }}
        >
          Your browser does not support the video tag.
        </video>
      </div>
    </div>
  );
}
