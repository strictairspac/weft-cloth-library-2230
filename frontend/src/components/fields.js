import {esc} from '../utils/dom.js';

export function fields(sample, labels) {
  return Object.entries(sample).map(([key, value], index)=>{
    const field = `business-${index}`;
    const label = esc(labels[key] || key);
    if (Array.isArray(value) || (value && typeof value === 'object')) {
      const columns = Array.isArray(value) && value[0] && typeof value[0] === 'object' && !Array.isArray(value[0])
        ? Object.keys(value[0]).map(key=>labels[key] || key).join(' · ') : '';
      const json = JSON.stringify(value, null, 2);
      return `<label class="field data"><span>${label}</span>${columns ? `<small>${esc(columns)}</small>`:''}<textarea id="${field}" rows="${Math.max(4,Math.min(9,json.split('\n').length))}" spellcheck="false">${esc(json)}</textarea></label>`;
    }
    if (typeof value === 'boolean') return `<label class="field"><span>${label}</span><select id="${field}"><option value="true" ${value?'selected':''}>启用</option><option value="false" ${value?'':'selected'}>停用</option></select></label>`;
    const type = typeof value === 'number' ? 'number' : 'text';
    return `<label class="field"><span>${label}</span><input id="${field}" type="${type}" ${type==='number'?'step="any"':''} value="${esc(value ?? '')}" required></label>`;
  }).join('');
}

export function readFields(sample, labels) {
  const result = Object.create(null);
  Object.entries(sample).forEach(([key, value], index)=>{
    const raw = document.getElementById(`business-${index}`).value;
    try {
      if (typeof value === 'number') {
        if (!raw || !Number.isFinite(Number(raw))) throw new Error();
        result[key] = Number(raw);
      } else if (typeof value === 'string') result[key] = raw;
      else result[key] = JSON.parse(raw);
    } catch {
      throw new Error(`请检查「${labels[key] || key}」的格式。`);
    }
  });
  return result;
}
