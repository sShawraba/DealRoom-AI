import client from './client';

export const getInvite = (token) => client.get(`/invites/${token}`).then((r) => r.data);
export const acceptInvite = (token, data) => client.post(`/invites/${token}/accept`, data).then((r) => r.data);
