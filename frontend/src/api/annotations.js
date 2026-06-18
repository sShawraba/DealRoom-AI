import client from './client';

export const create = (dealRoomId, data) =>
  client.post(`/deal-rooms/${dealRoomId}/annotations`, data).then((r) => r.data);

export const listByDealRoom = (dealRoomId, params) =>
  client.get(`/deal-rooms/${dealRoomId}/annotations`, { params }).then((r) => r.data);

export const resolve = (annotationId) =>
  client.patch(`/annotations/${annotationId}`, { resolved: true }).then((r) => r.data);

export const reply = (annotationId, data) =>
  client.post(`/annotations/${annotationId}/replies`, data).then((r) => r.data);
