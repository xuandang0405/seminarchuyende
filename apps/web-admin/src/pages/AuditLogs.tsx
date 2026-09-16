import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { FileText, Clock, User, Tag, RefreshCw, AlertCircle } from 'lucide-react';

interface AuditLog {
  _id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  metadata?: Record<string, any>;
  timestamp: string;
}

export const AuditLogs: React.FC = () => {
  const { token } = useAuth();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/v1/admin/audit-logs?limit=50', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Không thể nạp nhật ký kiểm toán');
      const data = await res.json();
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Lỗi nạp nhật ký');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [token]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Nhật Ký Kiểm Toán (Audit Logs)</h1>
          <p className="text-sm text-slate-500 mt-1">
            Ghi nhận toàn bộ thao tác quản trị, thay đổi nội dung và kiểm duyệt (Use Case S04)
          </p>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium transition-colors shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Làm Mới</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 flex items-center space-x-3 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-400">Đang nạp nhật ký...</div>
      ) : logs.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-slate-200/80 shadow-sm text-slate-500">
          <FileText className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <p className="font-medium">Chưa có nhật ký kiểm toán nào</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3.5 px-4">Thời Gian</th>
                  <th className="py-3.5 px-4">Tài Khoản</th>
                  <th className="py-3.5 px-4">Hành Động</th>
                  <th className="py-3.5 px-4">Tài Nguyên</th>
                  <th className="py-3.5 px-4">Chi Tiết (Metadata)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {logs.map((log) => (
                  <tr key={log._id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-500">
                      <div className="flex items-center space-x-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        <span>{new Date(log.timestamp).toLocaleString('vi-VN')}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs text-indigo-600 font-medium">
                      <div className="flex items-center space-x-1.5">
                        <User className="w-3.5 h-3.5 text-indigo-400" />
                        <span>{log.user_id.slice(0, 8)}...</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      <span className="inline-block px-2.5 py-1 rounded-md bg-slate-100 text-slate-800 text-xs font-mono">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs">
                      <div className="flex items-center space-x-1">
                        <Tag className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-medium text-slate-800">{log.resource_type}</span>
                        {log.resource_id && (
                          <span className="text-slate-400 font-mono">({log.resource_id.slice(0, 6)})</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-xs font-mono text-slate-600 max-w-xs truncate">
                      {log.metadata ? JSON.stringify(log.metadata) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
