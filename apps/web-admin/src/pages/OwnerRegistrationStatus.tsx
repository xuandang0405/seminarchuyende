import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Store, Clock, CheckCircle2, ArrowRight } from 'lucide-react';

export const OwnerRegistrationStatus: React.FC = () => {
  const { user } = useAuth();

  const isApproved = user?.is_poi_owner_verified;

  return (
    <div className="max-w-2xl mx-auto space-y-6 font-['Plus_Jakarta_Sans',sans-serif]">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Trạng Thái Đăng Ký Chủ Quán</h1>
        <p className="text-sm text-slate-500 mt-1">
          Theo dõi tiến trình thẩm định và xét duyệt hồ sơ quản lý địa điểm du lịch Quận 4.
        </p>
      </div>

      <div className="bg-white rounded-3xl border border-slate-200/80 p-8 shadow-sm space-y-6 text-center">
        {isApproved ? (
          <>
            <div className="w-16 h-16 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-md shadow-emerald-500/10">
              <CheckCircle2 className="w-9 h-9" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-slate-800">Hồ Sơ Đã Được Phê Duyệt!</h2>
              <p className="text-sm text-slate-600 max-w-md mx-auto">
                Chúc mừng! Tài khoản của bạn đã được Quản trị viên cấp quyền quản lý địa điểm POI và thực đơn Quận 4.
              </p>
            </div>
            <div>
              <Link
                to="/owner"
                className="inline-flex items-center space-x-2 py-3 px-6 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-colors shadow-lg shadow-indigo-600/20"
              >
                <span>Truy Cập Cổng Chủ Quán (Owner Portal)</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </>
        ) : (
          <>
            <div className="w-16 h-16 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center mx-auto shadow-md shadow-amber-500/10">
              <Clock className="w-9 h-9" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-slate-800">Hồ Sơ Đang Trong Quá Trình Xét Duyệt</h2>
              <p className="text-sm text-slate-600 max-w-md mx-auto">
                Hồ sơ đăng ký của bạn (<span className="font-semibold text-slate-800">{user?.email}</span>) đang được
                Ban Quản Trị TourVoice Quận 4 tiến hành thẩm định thông tin kinh doanh.
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-xs text-slate-500 text-left space-y-2">
              <p className="font-semibold text-slate-700">Quy trình thẩm định bao gồm:</p>
              <ul className="list-disc list-inside space-y-1 text-slate-600">
                <li>Đối soát vị trí thực tế của quán tại địa bàn Quận 4.</li>
                <li>Xác thực thông tin liên hệ và giấy phép kinh doanh (nếu có).</li>
                <li>Thời gian xét duyệt thông thường: trong vòng 24 - 48 giờ làm việc.</li>
              </ul>
            </div>
            <div>
              <Link
                to="/account"
                className="inline-flex items-center space-x-2 text-sm font-semibold text-indigo-600 hover:text-indigo-700 transition-colors"
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
