import client from './client';

export const list = (params) => client.get('/deal-rooms', { params }).then((r) => r.data);
export const create = (data) => client.post('/deal-rooms', data).then((r) => r.data);
export const get = (id) => client.get(`/deal-rooms/${id}`).then((r) => r.data);
export const update = (id, data) => client.patch(`/deal-rooms/${id}`, data).then((r) => r.data);
export const remove = (id) => client.delete(`/deal-rooms/${id}`);
export const compare = (roomId1, roomId2) =>
  client.get('/deal-rooms/compare', { params: { ids: `${roomId1},${roomId2}` } }).then((r) => r.data);

export const listMembers = (id) => client.get(`/deal-rooms/${id}/members`).then((r) => r.data);
export const addMember = (id, data) => client.post(`/deal-rooms/${id}/members`, data).then((r) => r.data);
export const removeMember = (id, userId) => client.delete(`/deal-rooms/${id}/members/${userId}`);
export const updateMember = (id, userId, data) =>
  client.patch(`/deal-rooms/${id}/members/${userId}`, data).then((r) => r.data);
