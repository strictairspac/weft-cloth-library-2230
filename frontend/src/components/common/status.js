import {esc} from '../../utils/dom.js';
import {statusLabels} from '../../constants/workflow.js';
export function badge(status) {
  return `<span class="status" data-state="${esc(status)}">${esc(statusLabels[status] || status)}</span>`;
}
