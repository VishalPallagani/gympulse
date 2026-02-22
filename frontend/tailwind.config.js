/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#05060A',
        surface: '#0D1118',
        panel: '#121826',
        chrome: '#1C2433',
        accent: '#FF4FD8',
        accentStrong: '#FF22C2',
        blaze: '#FFB703',
        cyan: '#22D3EE',
        violet: '#8B5CF6',
        mint: '#2EE6A6',
        rose: '#FB7185',
        orange: '#F97316',
        adminAccent: '#A855F7'
      },
      fontFamily: {
        heading: ['"Space Grotesk"', 'sans-serif'],
        body: ['"Plus Jakarta Sans"', 'sans-serif'],
        display: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace']
      },
      boxShadow: {
        card: '0 18px 48px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.05)',
        glow: '0 0 0 1px rgba(255,79,216,0.28), 0 0 42px rgba(255,79,216,0.24)',
        violetGlow: '0 0 0 1px rgba(168,85,247,0.3), 0 0 30px rgba(168,85,247,0.25)'
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' }
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' }
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        pulseSoft: {
          '0%,100%': { boxShadow: '0 0 0 0 rgba(255,79,216,0.25)' },
          '50%': { boxShadow: '0 0 0 8px rgba(255,79,216,0)' }
        }
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
        shimmer: 'shimmer 2.4s linear infinite',
        'fade-up': 'fade-up .6s ease forwards',
        pulseSoft: 'pulseSoft 2.4s infinite'
      }
    }
  },
  plugins: []
};
