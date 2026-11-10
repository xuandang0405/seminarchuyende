import L from 'leaflet';

type Coordinate = [number, number];
type Label = { group: 'area' | 'water' | 'road' | 'street'; name: string; position: Coordinate };
type DistrictData = {
  bounds: [number, number, number, number];
  polygons: Record<'parks' | 'water', Coordinate[][][]>;
  lines: Record<'waterways' | 'paths' | 'streets' | 'avenues' | 'highways' | 'bridges', Coordinate[][]>;
  labels: Label[];
};

const latLng = ([lng, lat]: Coordinate): L.LatLngTuple => [lat, lng];
const attribution = '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> · <a href="https://protomaps.com/">Protomaps</a>';
const style = [
  ['waterways', '#b8dce4', 1.8],
  ['paths', '#d9cfb6', 0.7],
  ['streets', '#fffefa', 2],
  ['avenues', '#fffdf3', 4],
  ['highways', '#f8deb0', 5.5],
  ['bridges', '#fffdf3', 3.6],
] as const;

export async function loadDistrictBasemap(map: L.Map, signal: AbortSignal) {
  const response = await fetch('/assets/q4-map.json', { signal });
  if (!response.ok) throw new Error('District basemap unavailable');
  const data: DistrictData = await response.json();
  signal.throwIfAborted();

  const [west, south, east, north] = data.bounds;
  const bounds = L.latLngBounds([south, west], [north, east]);
  const renderer = L.canvas({ pane: 'district-geometry', padding: 0.3 });
  const lines = L.layerGroup();
  const labels = L.layerGroup();
  const geometry = L.layerGroup([renderer, lines], { attribution });
  for (const [group, color] of [['parks', '#dbe8cf'], ['water', '#b8dce4']] as const) {
    L.polygon(data.polygons[group].map(polygon => polygon.map(ring => ring.map(latLng))), {
      renderer, interactive: false, stroke: false, fillColor: color, fillOpacity: 1, fillRule: 'nonzero',
    }).addTo(lines);
  }
  const roads = style.map(([group, color, weight]) => {
    const coordinates = data.lines[group].map(line => line.map(latLng));
    const options = { renderer, interactive: false, smoothFactor: 0.65 };
    const casing = weight >= 3 ? L.polyline(coordinates, { ...options, color: '#d6c9b5', weight: weight + 1.4 }) : null;
    return { group, weight, casing, fill: L.polyline(coordinates, { ...options, color, weight }) };
  });
  // Keep the casing below adjoining road fills so intersections read as continuous streets.
  for (const road of roads) road.casing?.addTo(lines);
  for (const road of roads) road.fill.addTo(lines);

  const sortedLabels = [...data.labels].sort((a, b) => Number(b.name === 'Quận 4') - Number(a.name === 'Quận 4'));
  function update() {
    const zoom = map.getZoom();
    const factor = zoom >= 16 ? 1.25 : zoom >= 14.5 ? 1 : 0.75;
    for (const { group, weight, casing, fill } of roads) {
      casing?.setStyle({ weight: weight * factor + 1.2 });
      fill.setStyle({ weight: weight * factor, opacity: group === 'paths' && zoom < 15 ? 0 : 1 });
    }
    labels.clearLayers();
    const size = map.getSize();
    const occupied: { x: number; y: number; width: number }[] = [];
    for (const group of ['area', 'water', 'road', 'street']) {
      if (group === 'street' && zoom < 15) continue;
      for (const label of sortedLabels) {
        if (label.group !== group) continue;
        if (zoom < 15 && (label.name.startsWith('Khu phố ') || label.name.startsWith('Hẻm '))) continue;
        const position = latLng(label.position);
        const { x, y } = map.latLngToContainerPoint(position);
        const width = Math.max(25, label.name.length * 3.1);
        if (x - width < 9 || x + width > size.x - 9 || y < 18 || y > size.y - 23) continue;
        if (occupied.some(other => Math.abs(y - other.y) < 18 && Math.abs(x - other.x) < width + other.width + 8)) continue;
        occupied.push({ x, y, width });
        const text = document.createElement('span');
        text.textContent = label.name;
        L.marker(position, {
          pane: 'district-labels', interactive: false, keyboard: false,
          icon: L.divIcon({ html: text, className: `tv-map-label tv-map-label-${group}`, iconSize: [0, 0] }),
        }).addTo(labels);
      }
    }
  }
  geometry.addTo(map);
  labels.addTo(map);
  map.on('moveend', update);
  update();
  return { bounds, remove: () => {
    map.off('moveend', update);
    labels.remove();
    // Remove the paths before their shared canvas renderer.
    lines.clearLayers();
    geometry.remove();
  } };
}
