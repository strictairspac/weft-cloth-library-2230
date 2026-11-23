export function route() {
  const [key, id] = (location.hash.slice(1) || 'cases').split('/');
  return {key, id:Number(id) || 0};
}
export function go(to) {
  location.hash = to;
}
