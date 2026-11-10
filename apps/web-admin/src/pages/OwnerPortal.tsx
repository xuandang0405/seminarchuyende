import { poiService } from '../services/poiService';
import { useLiveRefresh } from '../services/useLiveRefresh';
import { useEffect, useState, type FormEvent } from 'react';
import { Bell, CheckCircle2, MapPin, Plus, Send, Store } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Badge, Button, Card, CardHeader, EmptyState, Input, Modal, PageHeader } from '../components/ui';

const blank = { name: '', description: '', address: '', latitude: '', longitude: '' };
const reviewStatus = {
  approved: { label: 'Đã duyệt', variant: 'success' },
  rejected: { label: 'Từ chối', variant: 'danger' },
  pending: { label: 'Chờ duyệt', variant: 'warning' },
} as const;

export function OwnerPortal() {
  const { token, fetchWithAuth } = useAuth();
  const [data, setData] = useState<{ places: any[]; proposals: any[]; notices: any[] }>();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [showDraft, setShowDraft] = useState(false);
  const [draft, setDraft] = useState(blank);
  const [sending, setSending] = useState(false);
  const [locating, setLocating] = useState(false);
  const [draftError, setDraftError] = useState('');
  const [editing, setEditing] = useState<string>();
  const [refining, setRefining] = useState(false);
  const [suggestion, setSuggestion] = useState('');

  const refine = async () => {
    setRefining(true);
    setDraftError('');
    setSuggestion('');
    try {
      const result = await poiService.refineDescription({
        poi_name: draft.name.trim(), current_description: draft.description.trim(),
        address: draft.address.trim(),
      });
      setSuggestion(result.refined_description);
    } catch (error) {
      setDraftError((error as Error).message);
    } finally {
      setRefining(false);
    }
  };

  const load = async (background = false) => {
    if (!background) setLoading(true);
    setLoadError(false);
    try {
      const responses = await Promise.all(
        ['pois', 'submissions', 'notifications'].map(path => fetchWithAuth('/api/v1/owner/' + path)),
      );
      if (responses.some(response => !response.ok)) throw new Error('Không tải được dữ liệu cơ sở.');
      const [places, proposals, notices] = await Promise.all(responses.map(response => response.json()));
      setData({ places, proposals, notices });
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useLiveRefresh(() => load(true), !!token);

  useEffect(() => { if (token) void load(); }, [token]);

  const field = (key: keyof typeof blank) => ({
    value: draft[key],
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = event.target.value;
      setDraft(current => ({ ...current, [key]: value }));
    },
  });

  const locate = () => {
    if (!navigator.geolocation) {
      setDraftError('Trình duyệt không hỗ trợ định vị. Bạn có thể nhập tọa độ.');
      return;
    }
    setLocating(true);
    setDraftError('');
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      setDraft(current => ({
        ...current, latitude: coords.latitude.toFixed(6), longitude: coords.longitude.toFixed(6),
      }));
      setLocating(false);
    }, () => {
      setDraftError('Chưa lấy được vị trí. Hãy cho phép định vị hoặc nhập tọa độ.');
      setLocating(false);
    }, { timeout: 10000, enableHighAccuracy: true });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSending(true);
    setDraftError('');
    try {
      const response = await fetchWithAuth('/api/v1/owner/submissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: editing ? 'update' : 'create',
          poi_id: editing,
          payload: {
            name: draft.name.trim(),
            description: draft.description.trim(),
            address: draft.address.trim(),
            ...(editing ? {} : { category: 'food', trigger_radius: 30, audio_priority: 5 }),
            location: { type: 'Point', coordinates: [Number(draft.longitude), Number(draft.latitude)] },
          },
        }),
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(typeof result.detail === 'string' ? result.detail : 'Chưa gửi được đề xuất. Hãy kiểm tra thông tin và thử lại.');
      }
      setSubmitted(true);
      setShowDraft(false);
      setDraft(blank);
      void load();
    } catch (error) {
      setDraftError((error as Error).message);
    } finally {
      setSending(false);
    }
  };

  const openDraft = () => {
    setEditing(undefined);
    setDraft(blank);
    setSuggestion('');
    setDraftError('');
    setShowDraft(true);
  };

  const editPlace = (place: NonNullable<typeof data>['places'][number]) => {
    const coordinates = place.location?.coordinates;
    setEditing(place._id);
    setDraft({
      name: place.name, description: place.description || '', address: place.address || '',
      longitude: coordinates?.[0]?.toString() || '', latitude: coordinates?.[1]?.toString() || '',
    });
    setSuggestion('');
    setDraftError('');
    setShowDraft(true);
  };

  const closeDraft = () => { if (!sending && !refining) setShowDraft(false); };

  return (
    <div className="console-page space-y-5 sm:space-y-6">
      <PageHeader title="Cơ sở của tôi" description="Gửi thông tin địa điểm và theo dõi kết quả xét duyệt."
        actions={<Button icon={<Plus size={18} />} onClick={openDraft}>Đề xuất địa điểm</Button>} />
      {submitted && <p className="console-notice" role="status"><CheckCircle2 size={19} aria-hidden="true" />
        <span>Đã gửi đề xuất. Kết quả xét duyệt sẽ xuất hiện trong mục Đề xuất đã gửi.</span></p>}

      {loading && <div className="console-panel px-4 py-10 text-center text-sm text-slate-400" role="status">Đang tải thông tin cơ sở…</div>}
      {!loading && loadError && <div className="console-error" role="alert">
        <span>Không tải được dữ liệu cơ sở.</span><Button variant="outline" size="sm" onClick={() => void load()}>Thử lại</Button>
      </div>}
      {!loading && !loadError && data && (
        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]">
          <div className="min-w-0 space-y-5">
            <Card>
              <CardHeader title={<span className="flex items-center gap-2"><Store size={19} aria-hidden="true" /> Địa điểm đã công bố</span>}
                action={<Badge>{data.places.length}</Badge>} />
              {data.places.length ? <ul className="divide-y divide-slate-800">
                {data.places.map(place => <li key={place._id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <div className="min-w-0 break-words"><p className="font-semibold">{place.name}</p>
                    <p className="text-sm text-slate-400">{place.address || 'Chưa cập nhật địa chỉ'}</p></div>
                  <Button type="button" size="sm" variant="outline" onClick={() => editPlace(place)}>Đề xuất chỉnh sửa</Button>
                </li>)}
              </ul> : <EmptyState title="Chưa có địa điểm được công bố"
                description="Địa điểm sẽ xuất hiện ở đây sau khi được quản trị viên duyệt." icon={<Store size={21} />} />}
            </Card>
            <Card>
              <CardHeader title={<span className="flex items-center gap-2"><Send size={18} aria-hidden="true" /> Đề xuất đã gửi</span>}
                action={<Badge>{data.proposals.length}</Badge>} />
              {data.proposals.length ? <ul className="divide-y divide-slate-800">
                {data.proposals.map(proposal => {
                  const status = reviewStatus[proposal.status as keyof typeof reviewStatus] || reviewStatus.pending;
                  return <li key={proposal._id} className="flex flex-wrap items-start justify-between gap-2 py-3">
                    <div className="min-w-0 break-words"><p className="font-semibold">{proposal.payload?.name || 'Đề xuất địa điểm'}</p>
                      <p className="text-sm text-slate-400">Gửi ngày {new Date(proposal.created_at).toLocaleDateString('vi-VN')}</p>
                      {proposal.admin_note && <p className="mt-1 text-sm text-slate-400">{proposal.admin_note}</p>}
                    </div>
                    <Badge variant={status.variant} showDot>{status.label}</Badge>
                  </li>;
                })}
              </ul> : <EmptyState title="Chưa gửi đề xuất nào" description="Gửi thông tin cơ sở để quản trị viên xét duyệt." icon={<Send size={20} />} />}
            </Card>
          </div>
          <Card>
            <CardHeader title={<span className="flex items-center gap-2"><Bell size={18} aria-hidden="true" /> Thông báo</span>}
              action={<Badge>{data.notices.length}</Badge>} />
            {data.notices.length ? <ul className="divide-y divide-slate-800">
              {data.notices.map(notice => <li key={notice._id} className="py-3 first:pt-0 last:pb-0">
                <p className="text-sm leading-relaxed">{notice.message}</p>
                <p className="mt-1 text-xs text-slate-400">{new Date(notice.created_at).toLocaleString('vi-VN')}</p>
              </li>)}
            </ul> : <p className="py-4 text-sm text-slate-400">Chưa có thông báo.</p>}
          </Card>
        </div>
      )}

      <Modal isOpen={showDraft} onClose={closeDraft} title={editing ? "Đề xuất chỉnh sửa" : "Đề xuất địa điểm mới"}
        description="Thông tin sẽ được gửi tới quản trị viên để xét duyệt.">
        <form onSubmit={submit} className="grid gap-4">
          <Input id="owner-name" label="Tên cơ sở" required minLength={2} maxLength={200} {...field('name')} />
          <div>
            <label className="field-label" htmlFor="owner-description">Mô tả cơ sở</label>
            <textarea id="owner-description" className="field-input" rows={3} required minLength={5} maxLength={10000}
              placeholder="Món nổi bật, không gian hoặc câu chuyện của cơ sở" {...field('description')} />
          </div>
          <Button type="button" variant="outline" size="sm" loading={refining}
            disabled={sending || draft.name.trim().length < 2} onClick={() => void refine()}>Gợi ý mô tả bằng AI</Button>
          {suggestion && <div className="rounded-xl border border-slate-800 p-3 space-y-2">
            <p className="text-sm whitespace-pre-line">{suggestion}</p>
            <Button type="button" size="sm" onClick={() => {
              setDraft(current => ({ ...current, description: suggestion }));
              setSuggestion('');
            }}>Dùng gợi ý</Button>
          </div>}
          <Input id="owner-address" label="Địa chỉ" {...field('address')} />
          <fieldset className="grid gap-3 rounded-xl border border-slate-800 p-3">
            <legend className="px-1 text-sm font-semibold">Vị trí trên bản đồ</legend>
            <p className="text-sm text-slate-400">Nhập tọa độ hoặc lấy vị trí khi bạn đang ở cơ sở.</p>
            <Button type="button" className="justify-self-start" variant="outline" size="sm" icon={<MapPin size={16} />}
              loading={locating} onClick={locate}>Lấy vị trí hiện tại</Button>
            <div className="grid gap-3 sm:grid-cols-2">
              <Input id="owner-latitude" label="Vĩ độ" type="number" min={-90} max={90} step="any" required {...field('latitude')} />
              <Input id="owner-longitude" label="Kinh độ" type="number" min={-180} max={180} step="any" required {...field('longitude')} />
            </div>
          </fieldset>
          {draftError && <p className="console-error" role="alert">{draftError}</p>}
          <div className="flex flex-wrap justify-end gap-2 border-t border-slate-800 pt-4">
            <Button type="button" variant="secondary" disabled={sending} onClick={closeDraft}>Quay lại</Button>
            <Button type="submit" loading={sending} disabled={locating || refining}>Gửi xét duyệt</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
