import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getInvite, acceptInvite } from '../api/invites';
import useAuthStore from '../store/authStore';

export default function AcceptInvite() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const { setAuth, logout, user: currentUser, token: currentToken } = useAuthStore();

  const [invite, setInvite] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [form, setForm] = useState({ full_name: '', password: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    if (!token) {
      setLoadError('Invalid invite link.');
      return;
    }
    getInvite(token)
      .then(setInvite)
      .catch((err) => {
        const detail = err.response?.data?.detail;
        setLoadError(detail ?? 'This invite link is invalid or has expired.');
      });
  }, [token]);

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    setSubmitting(true);
    try {
      const data = await acceptInvite(token, form);
      setAuth(data.access_token, null);
      navigate('/dashboard');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setSubmitError(Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : (detail ?? 'Failed to accept invite.'));
    } finally {
      setSubmitting(false);
    }
  };

  if (currentToken) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">DealRoom AI</h1>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center space-y-4">
            <p className="text-gray-700 text-sm">
              You are currently signed in as <span className="font-semibold">{currentUser?.email}</span>.
              You must sign out before accepting an invitation as a different user.
            </p>
            <button
              onClick={() => { logout(); }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
            >
              Sign out and continue
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="w-full border border-gray-300 text-gray-700 font-medium py-2.5 rounded-lg text-sm hover:bg-gray-50 transition-colors"
            >
              Go back to dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">DealRoom AI</h1>
          <p className="mt-2 text-gray-500">Accept your invitation</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          {loadError ? (
            <div className="text-center space-y-3">
              <p className="text-red-600 text-sm">{loadError}</p>
              <a href="/login" className="text-blue-600 hover:underline text-sm">Go to login</a>
            </div>
          ) : !invite ? (
            <p className="text-center text-sm text-gray-500">Loading invite…</p>
          ) : (
            <>
              <div className="mb-6 p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
                <p><span className="font-medium">{invite.invited_by_name}</span> has invited you to join
                {invite.deal_room_name ? (
                  <> <span className="font-medium">"{invite.deal_room_name}"</span> as <span className="font-medium">{invite.deal_room_role?.replace('_', ' ')}</span>.</>
                ) : ' DealRoom AI.'}
                </p>
                <p className="mt-1 text-blue-600">{invite.email}</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                {submitError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
                    {submitError}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
                  <input
                    type="text"
                    name="full_name"
                    value={form.full_name}
                    onChange={handleChange}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Jane Smith"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Choose a password</label>
                  <input
                    type="password"
                    name="password"
                    value={form.password}
                    onChange={handleChange}
                    required
                    minLength={8}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="••••••••"
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
                >
                  {submitting ? 'Setting up your account…' : 'Accept invitation'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
