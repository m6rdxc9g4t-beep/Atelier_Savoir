/** Configuration Tailwind d'Atelier Savoir.
 *  Recompiler après modification des templates : npm run css  (ou npm run css:watch)
 */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html', './static/js/**/*.js'],
  theme: {
    // Charte v2 « Linear » de la suite : Inter partout, base 13 px sur ordinateur (14 px sur téléphone).
    // Les tailles viennent de variables (static/css/app.css) qui changent sous 768 px.
    fontFamily: {
      sans: ['var(--atelier-font)'],
      mono: ['var(--atelier-font-mono)'],
    },
    fontSize: {
      xs: ['var(--t-meta)', { lineHeight: '1.4' }],
      sm: ['var(--t-small)', { lineHeight: '1.45' }],
      base: ['var(--t-base)', { lineHeight: '1.45' }],
      md: ['var(--t-strong)', { lineHeight: '1.5' }],
      lg: ['var(--t-title)', { lineHeight: '1.45' }],
      xl: ['var(--t-page)', { lineHeight: '1.35', letterSpacing: '-0.012em' }],
      '2xl': ['var(--t-screen)', { lineHeight: '1.3', letterSpacing: '-0.015em' }],
    },
    // Rayons 5 / 7 / 10 px (--atelier-radius-sm|md|lg).
    borderRadius: {
      none: '0',
      sm: 'var(--atelier-radius-sm)',
      DEFAULT: 'var(--atelier-radius-md)',
      md: 'var(--atelier-radius-md)',
      lg: 'var(--atelier-radius-lg)',
      full: '9999px',
    },
    extend: {
      colors: {
        // Couleurs de sens (données) : inchangées.
        ambre: { 100: '#FBEBC8', 300: '#F2CB78', 400: '#E8B04A', 500: '#D9962A', 600: '#B57A1C', 700: '#8A5C12' },
        emeraude: { 100: '#D3F0E4', 300: '#7FD3B0', 400: '#45B98D', 500: '#2A9C73', 600: '#1F7D5B', 700: '#175E45' },
        framboise: { 100: '#F7DDE2', 400: '#D9768A', 500: '#C2566B', 600: '#A03F54' },
        // Structure commune, crème en clair et bleu nuit en sombre (jetons --atelier-* de static/brand/atelier-brand.css), qui changent
        // de valeur en thème sombre (.dark) : pas de variante dark: à écrire, pas de modificateur d'opacité (/50).
        fond: 'var(--atelier-bg)',
        barre: 'var(--atelier-sidebar)',
        surface: { DEFAULT: 'var(--atelier-surface)', 2: 'var(--atelier-surface-2)' },
        selection: 'var(--atelier-surface-3)',
        survol: 'var(--atelier-surface-2)',
        texte: 'var(--atelier-text)',
        doux: 'var(--atelier-muted)',
        discret: 'var(--atelier-faint)',
        bord: { DEFAULT: 'var(--atelier-border)', doux: 'var(--atelier-border-soft)' },
        ligne: 'var(--atelier-line)',
        // La signature (violet de Savoir) ne sert qu'à l'accent : action principale, sélection, focus, liens.
        signature: { DEFAULT: 'var(--atelier-signature)', doux: 'var(--atelier-signature-soft)' },
        encre: 'var(--atelier-ink)',
        // États anormaux seulement.
        attention: 'var(--atelier-warn)',
        erreur: 'var(--atelier-down)',
      },
    },
  },
  plugins: [],
};
