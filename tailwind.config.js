/** Configuration Tailwind d'Atelier Savoir.
 *  Recompiler après modification des templates : npm run css  (ou npm run css:watch)
 */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html', './static/js/**/*.js'],
  theme: {
    extend: {
      colors: {
        ambre: { 100: '#FBEBC8', 300: '#F2CB78', 400: '#E8B04A', 500: '#D9962A', 600: '#B57A1C', 700: '#8A5C12' },
        emeraude: { 100: '#D3F0E4', 300: '#7FD3B0', 400: '#45B98D', 500: '#2A9C73', 600: '#1F7D5B', 700: '#175E45' },
        framboise: { 100: '#F7DDE2', 400: '#D9768A', 500: '#C2566B', 600: '#A03F54' },
        // Charte « néon monochrome » : structure de l'app dérivée de la couleur signature (violet #9B5DE5).
        // Jetons --atelier-* de static/brand/atelier-brand.css, qui changent de valeur en thème sombre (.dark) :
        // pas de variante dark: à écrire. Pas de modificateur d'opacité (/50) sur ces couleurs.
        fond: 'var(--atelier-bg)',
        surface: { DEFAULT: 'var(--atelier-surface)', 2: 'var(--atelier-surface-2)' },
        selection: 'var(--atelier-surface-3)',
        survol: 'var(--atelier-signature-faint)',
        texte: 'var(--atelier-text)',
        doux: 'var(--atelier-muted)',
        encre: 'var(--atelier-ink)',
        bord: { DEFAULT: 'var(--atelier-border)', doux: 'var(--atelier-border-soft)' },
        ligne: 'var(--atelier-line)',
        signature: 'var(--atelier-signature)',
      },
      fontFamily: {
        serif: ['Literata', 'Georgia', 'serif'],
        sans: ['"Instrument Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
