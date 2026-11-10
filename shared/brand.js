export const palette = {
  paper: '#f5f4ec',
  surface: '#fffef9',
  ink: '#192d26',
  muted: '#596b61',
  line: '#dce2d8',
  forest: '#173e33',
  accent: '#24614b',
  tint: '#e5eee2',
  mist: '#c4d6bb',
  warm: '#eee8d6',
  error: '#a13432',
};

export const languages = [
  ['vi', 'Tiếng Việt'], ['en', 'English'], ['fr', 'Français'],
  ['ja', '日本語'], ['ko', '한국어'], ['zh', '中文'],
];

export const brandPath = 'M3 13v-2m4 6V7m5 13V4m5 13V7m4 6v-2';

// Decorative harbor illustration. Coordinates are independent of navigation data.
export const harborArtwork = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" fill="none" preserveAspectRatio="xMidYMid slice">
  <rect width="640" height="360" fill="#173e33"/>
  <circle cx="465" cy="103" r="67" fill="#e9e1b9"/>
  <path fill="#446e5b" d="M0 221 92 176l54 26 58-26 54 38 44-28 85 30 74-31 60 22 119-58v211H0Z"/>
  <path fill="#6d927d" d="M0 245q119-40 235 0t222 2q86-34 183-12v125H0Z"/>
  <path fill="#285446" d="M0 274q106-29 214 3t218-1q94-37 208-15v99H0Z"/>
  <g stroke="#c4d6bb" stroke-width="1.5" opacity=".63">
    <path d="M0 291q102-32 213 3t224-2q100-38 203-12"/>
    <path d="M0 306q103-28 214 6t225-5q101-38 201-11"/>
    <path d="M0 322q104-25 215 9t226-8q102-36 199-12"/>
    <path d="M0 338q103-22 216 12t226-10q101-36 198-13"/>
  </g>
  <g fill="#e9e1b9">
    <path d="M364 228h138l-15 19H390z"/>
    <path d="M429 217v-76l-40 76zm8 0h43l-43-63z" opacity=".92"/>
    <circle cx="544" cy="121" r="2.5"/><circle cx="579" cy="94" r="2.5"/><circle cx="316" cy="91" r="2.5"/>
  </g>
  <path d="M285 106c35-20 49-16 69-5m187 46c20-14 38-13 59-4" stroke="#c4d6bb" opacity=".7"/>
</svg>`;

const categories = {
  historical: 'Di tích', history: 'Di tích', landmark: 'Di tích',
  culture: 'Văn hóa', cultural: 'Văn hóa', food: 'Ẩm thực', culinary: 'Ẩm thực', restaurant: 'Ẩm thực', bridge: 'Cầu và cảng',
  sightseeing: 'Tham quan', attraction: 'Tham quan', museum: 'Bảo tàng', temple: 'Tâm linh',
};

export function categoryLabel(category) {
  return Object.hasOwn(categories, category) ? categories[category] : 'Điểm tham quan';
}

export function searchText(value) {
  return value.toLocaleLowerCase('vi').normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd');
}
