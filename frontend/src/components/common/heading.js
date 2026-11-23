import {esc} from '../../utils/dom.js';
export function heading(title, description='', tools='') {
  return `<header class="page-heading"><div><h1>${esc(title)}</h1>${description ? `<p>${esc(description)}</p>` : ''}</div>${tools ? `<div class="actions">${tools}</div>` : ''}</header>`;
}
export function panel(title, content) {
  return `<section class="panel"><h2>${esc(title)}</h2>${content}</section>`;
}
