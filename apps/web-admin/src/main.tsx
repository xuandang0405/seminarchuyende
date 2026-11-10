import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './index.css';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { palette } from '../../../shared/brand';
import './theme.css';
(window as any).L = L;

for (const [name, value] of Object.entries(palette)) {
  document.documentElement.style.setProperty('--tv-' + name, value);
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
