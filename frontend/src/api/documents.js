import client from './client';

export const upload = (dealRoomId, files, onProgress) => {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  return client
    .post(`/deal-rooms/${dealRoomId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    })
    .then((r) => r.data);
};

export const list = (dealRoomId, params) =>
  client.get(`/deal-rooms/${dealRoomId}/documents`, { params }).then((r) => r.data);

export const download = (dealRoomId, docId) =>
  client.get(`/deal-rooms/${dealRoomId}/documents/${docId}/download`, { responseType: 'blob' });

export const remove = (dealRoomId, docId) =>
  client.delete(`/deal-rooms/${dealRoomId}/documents/${docId}`);
