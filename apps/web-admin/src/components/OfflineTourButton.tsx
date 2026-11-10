import React, { useState } from 'react';
import { downloadOfflineTour } from '../services/offline';
export default function OfflineTourButton({ tourId, userId, lang }: { tourId: string; userId: string; lang: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Tải thuyết minh ngoại tuyến');
  return <div className="mt-3 text-xs text-slate-300"><button disabled={busy} className="underline disabled:opacity-50" onClick={async () => {
    setBusy(true);
    try { await downloadOfflineTour(tourId, userId, lang, setMessage); }
    catch (error: any) { setMessage(error.message); }
    finally { setBusy(false); }
  }}>{message}</button><p className="mt-1 text-slate-500">Gồm nội dung và audio. Bản đồ nền, chỉ đường cần kết nối mạng.</p></div>;
}
