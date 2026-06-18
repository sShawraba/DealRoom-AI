import client from './client';

export const trigger = (dealRoomId) =>
  client.post(`/deal-rooms/${dealRoomId}/reports`).then((r) => r.data);

export const list = (dealRoomId, params) =>
  client.get(`/deal-rooms/${dealRoomId}/reports`, { params }).then((r) => r.data);

export const get = (dealRoomId, reportId) =>
  client.get(`/deal-rooms/${dealRoomId}/reports/${reportId}`).then((r) => r.data);

export const updateItem = (dealRoomId, reportId, itemId, data) =>
  client
    .patch(`/deal-rooms/${dealRoomId}/reports/${reportId}/items/${itemId}`, data)
    .then((r) => r.data);

export const changeStatus = (dealRoomId, reportId, data) =>
  client.post(`/deal-rooms/${dealRoomId}/reports/${reportId}/status`, data).then((r) => r.data);

export const approve = (dealRoomId, reportId) =>
  client
    .post(`/deal-rooms/${dealRoomId}/reports/${reportId}/status`, { status: 'approved' })
    .then((r) => r.data);
