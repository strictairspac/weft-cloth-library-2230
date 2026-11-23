import {esc} from '../../utils/dom.js';

export function records(headers, body, empty='当前没有记录。') {
  if (!body.length) return `<p class="empty">${esc(empty)}</p>`;
  return `<div class="table-scroll" data-wide="${headers.length > 8}"><table><thead><tr>${headers.map(x=>`<th scope="col">${esc(x)}</th>`).join('')}</tr></thead><tbody>
  ${body.map(row=>`<tr>${row.map(x=>`<td>${x}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function readable(value) {
  const timestamp = typeof value === 'string' && /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}(?::\d{2})?)(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!timestamp) return esc(value);
  const [, day, time, offset] = timestamp;
  return `<time class="timestamp" datetime="${esc(value)}">${day}<small>${time.replace(/^(\d{2}:\d{2}):00$/, '$1')} ${offset}</small></time>`;
}

export function entries(rows, labels={}) {
  const keys = Array.from(new Set(rows.flatMap(Object.keys)));
  return records(keys.map(key=>labels[key] || key), rows.map(row=>keys.map(key=>readable(row[key]))));
}
