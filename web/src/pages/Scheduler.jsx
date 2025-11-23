import { useEffect, useState } from 'react';
import { api } from '../services/api';

const Scheduler = () => {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [formData, setFormData] = useState({
    command: '',
    type: 'interval',
    enabled: true,
    interval_minutes: 60,
    run_time: '00:00',
    day_of_week: 0,
  });

  useEffect(() => {
    loadSchedules();
  }, []);

  const loadSchedules = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listSchedules();
      if (data.success) {
        setSchedules(data.schedules || []);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load schedules');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      setMessage(null);

      if (editingSchedule) {
        const data = await api.updateSchedule(editingSchedule.id, formData);
        if (data.success) {
          setMessage('Schedule updated successfully');
          setShowForm(false);
          setEditingSchedule(null);
          loadSchedules();
        }
      } else {
        const data = await api.createSchedule(formData);
        if (data.success) {
          setMessage('Schedule created successfully');
          setShowForm(false);
          resetForm();
          loadSchedules();
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save schedule');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async scheduleId => {
    if (!confirm('Are you sure you want to delete this schedule?')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await api.deleteSchedule(scheduleId);
      if (data.success) {
        setMessage('Schedule deleted successfully');
        loadSchedules();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete schedule');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = schedule => {
    setEditingSchedule(schedule);
    setFormData({
      command: schedule.command || '',
      type: schedule.type || 'interval',
      enabled: schedule.enabled !== false,
      interval_minutes: schedule.interval_minutes || 60,
      run_time: schedule.run_time || '00:00',
      day_of_week: schedule.day_of_week || 0,
    });
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      command: '',
      type: 'interval',
      enabled: true,
      interval_minutes: 60,
      run_time: '00:00',
      day_of_week: 0,
    });
    setEditingSchedule(null);
  };

  const formatLastRun = lastRun => {
    if (!lastRun) return 'Never';
    try {
      const date = new Date(lastRun);
      return date.toLocaleString();
    } catch {
      return lastRun;
    }
  };

  const getScheduleDescription = schedule => {
    if (schedule.type === 'interval') {
      return `Every ${schedule.interval_minutes} minutes`;
    } else if (schedule.type === 'daily') {
      return `Daily at ${schedule.run_time}`;
    } else if (schedule.type === 'weekly') {
      const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
      return `Weekly on ${days[schedule.day_of_week || 0]} at ${schedule.run_time}`;
    }
    return 'Unknown';
  };

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        COMMAND SCHEDULER
      </h1>

      {message && (
        <div className="card-minecraft p-4 mb-6 bg-minecraft-grass-DEFAULT text-white">
          <div className="text-[10px] font-minecraft">{message}</div>
        </div>
      )}

      {error && (
        <div className="card-minecraft p-4 mb-6 bg-[#C62828] text-white">
          <div className="text-[10px] font-minecraft">{error}</div>
        </div>
      )}

      <div className="mb-6">
        <button
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
          className="btn-minecraft-primary text-[10px]"
        >
          + CREATE SCHEDULE
        </button>
      </div>

      {showForm && (
        <div className="card-minecraft p-6 mb-6">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
            {editingSchedule ? 'EDIT SCHEDULE' : 'CREATE SCHEDULE'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
                COMMAND
              </label>
              <input
                type="text"
                value={formData.command}
                onChange={e => setFormData({ ...formData, command: e.target.value })}
                required
                placeholder="e.g. say Server restart in 5 minutes"
                className="input-minecraft w-full text-[10px]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
                SCHEDULE TYPE
              </label>
              <select
                value={formData.type}
                onChange={e => setFormData({ ...formData, type: e.target.value })}
                className="input-minecraft w-full text-[10px]"
              >
                <option value="interval">Interval (Every X minutes)</option>
                <option value="daily">Daily (At specific time)</option>
                <option value="weekly">Weekly (On specific day)</option>
              </select>
            </div>

            {formData.type === 'interval' && (
              <div>
                <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
                  INTERVAL (MINUTES)
                </label>
                <input
                  type="number"
                  value={formData.interval_minutes}
                  onChange={e =>
                    setFormData({ ...formData, interval_minutes: Number(e.target.value) })
                  }
                  min={1}
                  required
                  className="input-minecraft w-full text-[10px]"
                />
              </div>
            )}

            {(formData.type === 'daily' || formData.type === 'weekly') && (
              <div>
                <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
                  RUN TIME (HH:MM)
                </label>
                <input
                  type="time"
                  value={formData.run_time}
                  onChange={e => setFormData({ ...formData, run_time: e.target.value })}
                  required
                  className="input-minecraft w-full text-[10px]"
                />
              </div>
            )}

            {formData.type === 'weekly' && (
              <div>
                <label className="block text-[10px] font-minecraft text-minecraft-text-light mb-2">
                  DAY OF WEEK
                </label>
                <select
                  value={formData.day_of_week}
                  onChange={e => setFormData({ ...formData, day_of_week: Number(e.target.value) })}
                  className="input-minecraft w-full text-[10px]"
                >
                  <option value={0}>Monday</option>
                  <option value={1}>Tuesday</option>
                  <option value={2}>Wednesday</option>
                  <option value={3}>Thursday</option>
                  <option value={4}>Friday</option>
                  <option value={5}>Saturday</option>
                  <option value={6}>Sunday</option>
                </select>
              </div>
            )}

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={e => setFormData({ ...formData, enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label
                htmlFor="enabled"
                className="text-[10px] font-minecraft text-minecraft-text-light"
              >
                ENABLED
              </label>
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                className="btn-minecraft-primary text-[10px]"
                disabled={loading}
              >
                {editingSchedule ? 'UPDATE' : 'CREATE'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  resetForm();
                }}
                className="btn-minecraft text-[10px]"
              >
                CANCEL
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card-minecraft p-4">
        {loading && !schedules.length ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING...
          </div>
        ) : schedules.length === 0 ? (
          <div className="text-center py-8 text-minecraft-text-dark text-[10px] font-minecraft">
            NO SCHEDULES. CREATE ONE ABOVE.
          </div>
        ) : (
          <div className="space-y-2">
            {schedules.map(schedule => (
              <div
                key={schedule.id}
                className={`p-4 border-2 ${
                  schedule.enabled
                    ? 'border-minecraft-grass-DEFAULT bg-minecraft-dirt-DEFAULT'
                    : 'border-minecraft-stone-DEFAULT bg-minecraft-dirt-DEFAULT opacity-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[10px] font-minecraft text-minecraft-text-light">
                        {schedule.enabled ? '✓' : '✗'}
                      </span>
                      <code className="text-[10px] font-minecraft text-minecraft-water-light">
                        {schedule.command}
                      </code>
                    </div>
                    <div className="text-[10px] font-minecraft text-minecraft-text-dark">
                      {getScheduleDescription(schedule)}
                    </div>
                    <div className="text-[8px] font-minecraft text-minecraft-text-dark mt-1">
                      Last run: {formatLastRun(schedule.last_run)}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(schedule)}
                      className="btn-minecraft text-[10px]"
                    >
                      EDIT
                    </button>
                    <button
                      onClick={() => handleDelete(schedule.id)}
                      className="btn-minecraft text-[10px] bg-[#C62828]"
                    >
                      DELETE
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Scheduler;
