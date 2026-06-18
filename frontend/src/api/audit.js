import client from './client';

export const list = (params) => client.get('/audit-log', { params }).then((r) => r.data);

export const exportCSV = (params) =>
  client.get('/audit-log/export', { params, responseType: 'blob' });
