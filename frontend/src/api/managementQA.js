import client from './client';

export const generate = (dealRoomId, reportId) =>
  client.post(`/deal-rooms/${dealRoomId}/reports/${reportId}/qa/generate`).then((r) => r.data);

export const list = (dealRoomId, reportId, params) =>
  client.get(`/deal-rooms/${dealRoomId}/reports/${reportId}/qa`, { params }).then((r) => r.data);

export const answer = (questionId, data) =>
  client.patch(`/management-questions/${questionId}/answer`, data).then((r) => r.data);

export const sendEmail = (dealRoomId, reportId, data) =>
  client
    .post(`/deal-rooms/${dealRoomId}/reports/${reportId}/qa/send-email`, data)
    .then((r) => r.data);
