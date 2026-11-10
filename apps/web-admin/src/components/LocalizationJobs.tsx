import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../config/runtime';
import { apiClient } from '../services/apiClient';

export default function LocalizationJobs({ ids, onDone }: { ids: string[]; onDone: () => void }) {
  const [tasks, setTasks] = useState<any[]>([]);
  const [error, setError] = useState('');
  const done = useRef(onDone);
  done.current = onDone;
  useEffect(() => {
    setTasks([]);
    setError('');
    const taskIds = [...new Set(ids)];
    if (!taskIds.length) return;
    const controller = new AbortController();
    let timer: number | undefined;
    const query = new URLSearchParams();
    taskIds.forEach(id => query.append('task_id', id));
    const source = new EventSource(apiUrl('/audio/tasks/events?' + query), { withCredentials: true });

    function accept(values: any[]) {
      if (controller.signal.aborted) return true;
      setTasks(values);
      setError('');
      if (values.every(task => ['succeeded', 'failed', 'cancelled'].includes(task.status))) {
        done.current();
        return true;
      }
      return false;
    }

    async function poll() {
      if (controller.signal.aborted) return;
      try {
        const values = await Promise.all(taskIds.map(id => apiClient.get(
          '/audio/tasks/' + encodeURIComponent(id), { signal: controller.signal },
        )));
        if (accept(values)) return;
      } catch (e) {
        if (!controller.signal.aborted) setError((e as Error).message);
      }
      if (!controller.signal.aborted) timer = window.setTimeout(poll, 3000);
    }

    source.onmessage = event => {
      const values = JSON.parse(event.data);
      if (values.some((task: unknown) => !task)) { source.close(); void poll(); return; }
      if (accept(values)) source.close();
    };
    source.onerror = () => {
      source.close();
      void poll();
    };
    return () => {
      controller.abort();
      source.close();
      window.clearTimeout(timer);
    };
  }, [ids]);
  const labels: Record<string, string> = { queued: 'Đang chờ worker', running: 'Đang xử lý', paused: 'Đã tạm dừng',
    succeeded: 'Đã xử lý', failed: 'Thất bại', cancelled: 'Đã hủy' };
  return <div className="space-y-2" aria-live="polite">{error && <p className="text-rose-400 text-sm">{error}</p>}
    {tasks.map(task => <div key={task._id} className="p-3 rounded bg-slate-900 border border-slate-700 text-sm text-slate-300">
      {labels[task.status] || task.status}: {task.progress?.completed || 0}/{task.progress?.total || 0}
      {task.error_message && <span className="block text-amber-400">{task.error_message}</span>}
      {['queued', 'running', 'paused'].includes(task.status) && <div className="flex gap-3 mt-2">
        {['paused', 'queued'].includes(task.status) && task.pause_requested ?
          <button onClick={() => void apiClient.post('/audio/tasks/' + task._id + '/resume').catch(e => setError(e.message))}>Tiếp tục</button> :
          <button disabled={task.pause_requested} onClick={() => void apiClient.post('/audio/tasks/' + task._id + '/pause').catch(e => setError(e.message))}>
            {task.pause_requested ? 'Đang tạm dừng…' : 'Tạm dừng'}</button>}
        <button onClick={() => void apiClient.post('/audio/tasks/' + task._id + '/cancel').catch(e => setError(e.message))}>Hủy tác vụ</button>
      </div>}
    </div>)}</div>;
}
