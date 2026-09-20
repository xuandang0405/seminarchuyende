import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Store, Clock, CheckCircle2, ArrowRight } from 'lucide-react';
import { PageHeader, Button } from '../components/ui';

export const OwnerRegistrationStatus: React.FC = () => {
  const { user } = useAuth();

  const isApproved = user?.is_poi_owner_verified;

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto space-y-6 font-['Plus_Jakarta_Sans',sans-serif]">
      <PageHeader
        title="Trạng Thái Đăng Ký Chủ Quán"
        description="Theo dõi tiến trình thẩm định và xét duyệt hồ sơ quản lý địa điểm du lịch Quận 4"
      />

      <div className="bg-slate-900/60 backdrop-blur-md rounded-3xl border border-slate-800 p-8 shadow-2xl space-y-6 text-center">
        {isApproved ? (
          <>
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="w-9 h-9" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-white">Hồ Sơ Đã Được Phê Duyệt!</h2>
              <p className="text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
                Chúc mừng! Tài khoản của bạn đã được Quản trị viên cấp quyền quản lý địa điểm POI và thực đơn Quận 4.
              </p>
            </div>
            <div className="pt-2">
              <Link
                to="/owner"
                className="inline-flex items-center space-x-2 py-3 px-6 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-indigo-600/25"
              >
                <span>Truy Cập Cổng Chủ Quán (Owner Portal)</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </>
        ) : (
          <>
            <div className="w-16 h-16 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center mx-auto shadow-lg shadow-amber-500/20">
              <Clock className="w-9 h-9" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-white">Hồ Sơ Đang Trong Quá Trình Xét Duyệt</h2>
              <p className="text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
                Hồ sơ đăng ký của bạn (<span className="font-semibold text-white">{user?.email}</span>) đang được
                Ban Quản Trị TourVoice Quận 4 tiến hành thẩm định thông tin kinh doanh.
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs text-slate-400 text-left space-y-2 max-w-md mx-auto">
              <p className="font-semibold text-slate-300">Quy trình thẩm định bao gồm:</p>
              <ul className="list-disc list-inside space-y-1.5 text-slate-400">
                <li>Đối soát vị trí thực tế của quán tại địa bàn Quận 4.</li>
                <li>Xác thực thông tin liên hệ và giấy phép kinh doanh (nếu có).</li>
                <li>Thời gian xét duyệt thông thường: trong vòng 24 - 48 giờ làm việc.</li>
              </ul>
            </div>
            <div className="pt-2">
              <Link
                to="/account"
                className="inline-flex items-center space-x-2 text-sm font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <span>Xem thông tin tài khoản của bạn</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
