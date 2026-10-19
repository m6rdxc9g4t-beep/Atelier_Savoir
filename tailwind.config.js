/** Configuration Tailwind d'Atelier Savoir.
 *  Recompiler après modification des templates : npm run css  (ou npm run css:watch)
 */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html', './static/js/**/*.js'],
  theme: {
    extend: {
      colors: {
        nuit: {
          50: '#EEF2F8', 100: '#DCE4F0', 200: '#B6C5DD', 300: '#8AA0C2', 400: '#5E78A0',
          500: '#3F5880', 600: '#2C4366', 700: '#22344F', 800: '#1A283D', 900: '#13202F', 950: '#0C1624',
        },
        ambre: { 100: '#FBEBC8', 300: '#F2CB78', 400: '#E8B04A', 500: '#D9962A', 600: '#B57A1C', 700: '#8A5C12' },
        emeraude: { 100: '#D3F0E4', 300: '#7FD3B0', 400: '#45B98D', 500: '#2A9C73', 600: '#1F7D5B', 700: '#175E45' },
        framboise: { 100: '#F7DDE2', 400: '#D9768A', 500: '#C2566B', 600: '#A03F54' },
        papier: '#F4F6FA',
      },
      fontFamily: {
        serif: ['Literata', 'Georgia', 'serif'],
        sans: ['"Instrument Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
