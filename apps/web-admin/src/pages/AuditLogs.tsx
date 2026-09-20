import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { FileText, Clock, User, Tag, RefreshCw, AlertCircle } from 'lucide-react';
import { PageHeader, Button, Card, Badge, EmptyState } from '../components/ui';

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
    <div className="p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto font-['Plus_Jakarta_Sans',sans-serif]">
      <PageHeader
        title="Nhật Ký Kiểm Toán (Audit Logs)"
        description="Ghi nhận toàn bộ thao tác quản trị, thay đổi nội dung và kiểm duyệt hệ thống"
        actions={
          <Button
            variant="secondary"
            size="md"
            onClick={fetchLogs}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            <span>Làm Mới</span>
          </Button>
        }
      />

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center space-x-3 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="p-16 text-center text-slate-500 font-medium">Đang nạp nhật ký kiểm toán...</div>
      ) : logs.length === 0 ? (
        <EmptyState
          title="Chưa có nhật ký kiểm toán"
          description="Hệ thống chưa ghi nhận thao tác thay đổi dữ liệu nào gần đây."
          icon={<FileText className="w-8 h-8 text-slate-500" />}
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 text-xs uppercase tracking-wider">
                <tr>
                  <th className="py-4 px-5">Thời Gian</th>
                  <th className="py-4 px-5">Tài Khoản</th>
                  <th className="py-4 px-5">Hành Động</th>
                  <th className="py-4 px-5">Tài Nguyên</th>
                  <th className="py-4 px-5">Chi Tiết (Metadata)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300 text-xs font-mono">
                {logs.map((log) => (
                  <tr key={log._id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-4 px-5 whitespace-nowrap text-slate-400 font-sans">
                      <div className="flex items-center space-x-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        <span>{new Date(log.timestamp).toLocaleString('vi-VN')}</span>
                      </div>
                    </td>
                    <td className="py-4 px-5 text-indigo-400 font-medium font-sans">
                      <div className="flex items-center space-x-1.5">
                        <User className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                        <span className="truncate max-w-[120px]">{log.user_id}</span>
                      </div>
                    </td>
                    <td className="py-4 px-5">
                      <Badge variant="purple" size="sm">
                        {log.action}
                      </Badge>
                    </td>
                    <td className="py-4 px-5 font-sans">
                      <div className="flex items-center space-x-1.5 text-slate-300">
                        <Tag className="w-3.5 h-3.5 text-slate-500" />
                        <span className="font-semibold text-white">{log.resource_type}</span>
                        {log.resource_id && (
                          <span className="text-slate-500 font-mono text-[11px]">({log.resource_id.slice(0, 8)})</span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-5 text-slate-400 max-w-sm truncate text-[11px]">
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
