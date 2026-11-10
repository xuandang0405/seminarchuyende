// Run from apps/web-admin after installing pmtiles, @mapbox/vector-tile and pbf
// with npm install --no-save --package-lock=false.
import { writeFile } from 'node:fs/promises';
import { PMTiles } from 'pmtiles';
import { VectorTile } from '@mapbox/vector-tile';
import { PbfReader } from 'pbf';

const source = process.argv[2] || 'https://build.protomaps.com/20261108.pmtiles';
const output = process.argv[3] || 'public/assets/q4-map.json';
const archive = new PMTiles(source);
const zoom = 15;
const scale = 2 ** zoom;
const [west, south, east, north] = [106.665, 10.721, 106.745, 10.798];
const toTileX = lon => Math.floor((lon + 180) / 360 * scale);
const toTileY = lat => Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * scale);
const minX = toTileX(west), maxX = toTileX(east);
const minY = toTileY(north), maxY = toTileY(south);
const district = { minX: toTileX(106.685), maxX: toTileX(106.720), minY: toTileY(10.775), maxY: toTileY(10.745) };
const polygons = { parks: [], water: [] };
const lines = { paths: [], streets: [], avenues: [], highways: [], bridges: [], waterways: [] };
const labelCandidates = new Map();
const seen = new Set();
const parks = new Set(['forest', 'garden', 'grass', 'park', 'recreation_ground', 'wood']);
const arterial = new Set(['primary', 'secondary', 'tertiary', 'trunk', 'motorway']);
const round = value => Math.round(value * 100000) / 100000;

function coord(x, y) {
  return [round(x / scale * 360 - 180), round(Math.atan(Math.sinh(Math.PI * (1 - 2 * y / scale))) * 180 / Math.PI)];
}

function label(group, name, position, weight) {
  const key = group + ':' + name;
  if (weight > (labelCandidates.get(key)?.weight ?? 0)) labelCandidates.set(key, { group, name, position, weight });
}

function length(line) {
  return line.slice(1).reduce((sum, [x, y], i) => sum + Math.hypot(x - line[i][0], y - line[i][1]), 0);
}

const tiles = [];
for (let x = minX; x <= maxX; x++) for (let y = minY; y <= maxY; y++) tiles.push([x, y]);
for (let offset = 0; offset < tiles.length; offset += 6) {
  const batch = await Promise.all(tiles.slice(offset, offset + 6).map(async ([x, y]) => [x, y, await archive.getZxy(zoom, x, y)]));
  for (const [x, y, tile] of batch) {
    if (!tile) throw new Error(`Missing source tile ${zoom}/${x}/${y}`);
    const districtDetail = x >= district.minX && x <= district.maxX && y >= district.minY && y <= district.maxY;
    const { layers } = new VectorTile(new PbfReader(new Uint8Array(tile.data)));
    for (const layerName of ['landuse', 'water', 'roads', 'places', 'pois']) {
      const layer = layers[layerName];
      if (!layer) continue;
      for (let i = 0; i < layer.length; i++) {
        const feature = layer.feature(i);
        const { kind, kind_detail: detail, name, is_bridge: bridge } = feature.properties;
        const named = feature.properties['name:vi'] || name;
        const geometry = feature.toGeoJSON(x, y, zoom).geometry;
        if (geometry.type === 'Point') {
          if (named && (layerName === 'places' || layerName === 'pois' && kind === 'historic' && feature.properties.min_zoom <= 12)) {
            label('area', named, geometry.coordinates.map(round), 1);
          }
        } else if (geometry.type === 'Polygon' || geometry.type === 'MultiPolygon') {
          const bucket = layerName === 'water' && !['fountain', 'swimming_pool'].includes(kind) ? polygons.water
            : layerName === 'landuse' && parks.has(kind) ? polygons.parks : null;
          if (!bucket) continue;
          const parts = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
          for (const rings of parts) {
            bucket.push(rings.map(ring => ring.map(point => point.map(round))));
          }
        } else if (geometry.type === 'LineString' || geometry.type === 'MultiLineString') {
          const group = layerName === 'water' ? 'waterways' : layerName !== 'roads' ? null
            : bridge && kind !== 'path' ? 'bridges'
            : kind === 'highway' || detail === 'trunk' || detail === 'motorway' ? 'highways'
            : kind === 'major_road' || arterial.has(detail) ? 'avenues'
            : kind === 'minor_road' ? 'streets' : kind === 'path' ? 'paths' : null;
          if (!group) continue;
          if (group === 'paths' && !districtDetail) continue;
          if (group === 'streets' && (detail === 'service' || !districtDetail && !named)) continue;
          const parts = geometry.type === 'LineString' ? [geometry.coordinates] : geometry.coordinates;
          for (const part of parts) {
            const points = part.map(point => point.map(round));
            const key = JSON.stringify(points);
            if (seen.has(key)) continue;
            seen.add(key);
            lines[group].push(points);
            if (named && group !== 'paths' && (group !== 'streets' || districtDetail && !/^(Hẻm|Ngõ)\b/iu.test(named))) {
              const labelGroup = group === 'streets' ? 'street' : group === 'waterways' ? 'water' : 'road';
              const middle = Math.floor(points.length / 2);
              const position = points[middle].map((value, axis) => round((value + points[middle - 1][axis]) / 2));
              label(labelGroup, named, position, length(points));
            }
          }
        }
      }
    }
  }
}
const labels = [...labelCandidates.values()].sort((a, b) => b.weight - a.weight).map(({ group, name, position }) => ({ group, name, position }));
const [left, top] = coord(minX, minY);
const [right, bottom] = coord(maxX + 1, maxY + 1);
const basemap = {
  source, license: 'https://www.openstreetmap.org/copyright',
  bounds: [left, bottom, right, top], polygons, lines, labels,
};
await writeFile(output, JSON.stringify(basemap) + '\n');
console.log(`Saved ${tiles.length} source tiles as district street geometry at ${output}`);
