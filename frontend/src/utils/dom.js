export const el = (name)=>document.createElement(name);
export const text = (value)=>typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? '—');
export const esc = (value)=>text(value).replace(/[&<>"']/g, ch=>({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[ch]));
export function date(value) {
  return value ? new Intl.DateTimeFormat('zh-CN', {dateStyle:'short', timeStyle:'medium', timeZone:'Asia/Shanghai'}).format(new Date(value)) : '—';
}
