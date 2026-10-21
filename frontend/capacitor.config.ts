import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.tachelhit.app',
  appName: 'Tamazight Drills',
  webDir: 'dist',
  ios: {
    // Let the web view run under the status bar; the app pads its own
    // headers with env(safe-area-inset-top) (see --nav-h in App.css).
    contentInset: 'never',
    preferredContentMode: 'mobile',
  },
  plugins: {
    Keyboard: {
      // Resize the web view when the keyboard opens so fixed bottom bars
      // (copilot input, editor nav) stay visible.
      resize: 'native',
      resizeOnFullScreen: true,
    },
  },
};

export default config;
