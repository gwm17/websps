/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html, js}", "./../templates/**/*.html"],
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      'garnet': '#782f40',
      'light-garnet': '#b34760',
      'gold': '#ceb888',
      'light-gold': '#e7dcc4',
      'white': '#f4f4f4',
      'neutral': '#969594',
      'light-slate': '#565554',
      'slate': '#2c2a29',
      'black': '#161514'
    },
    extend: {},
  },
  plugins: [],
}
