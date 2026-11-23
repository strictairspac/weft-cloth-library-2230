export async function request(path, {method='GET', data, token, response=false}={}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const result = await fetch(`/api${path}`, {method, headers, body: data === undefined ? undefined : JSON.stringify(data)});
  if (!result.ok) {
    const body = await result.json().catch(() => ({}));
    const error = new Error(typeof body.detail === 'string' ? body.detail : '操作未完成，请检查输入后重试。');
    error.status = result.status;
    throw error;
  }
  return response ? result : result.json();
}
