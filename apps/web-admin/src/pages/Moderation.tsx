import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Clock, ShieldCheck, UserCheck, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Moderation: React.FC = () => {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<'registrations' | 'submissions'>('registrations');
  const [registrations, setRegistrations] = useState<any[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [adminNote, setAdminNote] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'registrations') {
        const res = await fetch('/api/v1/admin/moderation/registrations', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setRegistrations(Array.isArray(data) ? data : []);
      } else {
        const res = await fetch('/api/v1/admin/moderation/submissions', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setSubmissions(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, token]);

  const handleReviewRegistration = async (id: string, decision: 'approved' | 'rejected', version: number) => {
    setActionLoading(id);
    setMessage(null);
    try {
      const res = await fetch(`/api/v1/admin/moderation/registrations/${id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          decision,
          admin_note: adminNote || (decision === 'approved' ? 'Hồ sơ hợp lệ.' : 'Chưa đủ điều kiện.'),
          expected_version: version,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || 'Duyệt thất bại');

      setMessage({ type: 'success', text: `Đã ${decision === 'approved' ? 'chấp thuận' : 'từ chối'} hồ sơ chủ quán!` });
      setAdminNote('');
      fetchData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReviewSubmission = async (id: string, decision: 'approved' | 'rejected', version: number) => {
    setActionLoading(id);
    setMessage(null);
    try {
      const res = await fetch(`/api/v1/admin/moderation/submissions/${id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          decision,
          admin_note: adminNote || (decision === 'approved' ? 'Nội dung đạt chuẩn.' : 'Cần sửa đổi thêm.'),
          expected_version: version,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || 'Duyệt thất bại');

      setMessage({ type: 'success', text: `Đã ${decision === 'approved' ? 'phê duyệt' : 'từ chối'} đề xuất nội dung!` });
      setAdminNote('');
      fetchData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Trung Tâm Kiểm Duyệt (Moderation)</h1>
        <p className="text-sm text-slate-400 mt-1">
          Xét duyệt hồ sơ đăng ký chủ quán (C06) và kiểm duyệt nội dung đề xuất POI mới (C07)
        </p>
      </div>

      {message && (
        <div className={`p-4 rounded-xl text-sm font-medium flex items-center space-x-2 ${
          message.type === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab('registrations')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'registrations'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Hồ Sơ Đăng Ký Chủ Quán
        </button>
        <button
          onClick={() => setActiveTab('submissions')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'submissions'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Đề Xuất Nội Dung Chờ Duyệt
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-16 text-slate-400">Đang tải danh sách kiểm duyệt...</div>
      ) : activeTab === 'registrations' ? (
        registrations.length === 0 ? (
          <div className="text-center py-16 text-slate-500">Hiện không có hồ sơ chủ quán nào chờ duyệt.</div>
        ) : (
          <div className="space-y-4">
            {registrations.map((reg) => (
              <div key={reg._id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <UserCheck className="w-5 h-5 text-indigo-400" />
                    <h3 className="font-bold text-white text-base">{reg.business_name}</h3>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">User ID: {reg.user_id}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Ngày gửi: {new Date(reg.submitted_at).toLocaleString('vi-VN')} | Phiên bản: v{reg.version}
                  </p>
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  <button
                    onClick={() => handleReviewRegistration(reg._id, 'approved', reg.version)}
                    disabled={actionLoading === reg._id}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-600/20 disabled:opacity-50"
                  >
                    Chấp Thuận
                  </button>
                  <button
                    onClick={() => handleReviewRegistration(reg._id, 'rejected', reg.version)}
                    disabled={actionLoading === reg._id}
                    className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 rounded-xl text-xs font-semibold disabled:opacity-50"
                  >
                    Từ Chối
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        submissions.length === 0 ? (
          <div className="text-center py-16 text-slate-500">Hiện không có đề xuất nội dung nào chờ duyệt.</div>
        ) : (
          <div className="space-y-4">
            {submissions.map((sub) => (
              <div key={sub._id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between gap-4">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 text-xs font-semibold uppercase">
                      Hành động: {sub.action}
                    </span>
                    <span className="text-xs text-slate-500">
                      Gửi ngày: {new Date(sub.created_at).toLocaleString('vi-VN')}
                    </span>
                  </div>
                  <h3 className="font-bold text-white text-base mt-2">
                    {sub.payload?.name || 'Đề xuất mới'}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">{sub.payload?.description}</p>
                </div>

                <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800/80">
                  <button
                    onClick={() => handleReviewSubmission(sub._id, 'approved', sub.version)}
                    disabled={actionLoading === sub._id}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-600/20 disabled:opacity-50"
                  >
                    Phê Duyệt
                  </button>
                  <button
                    onClick={() => handleReviewSubmission(sub._id, 'rejected', sub.version)}
                    disabled={actionLoading === sub._id}
                    className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 rounded-xl text-xs font-semibold disabled:opacity-50"
                  >
                    Từ Chối
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
};
