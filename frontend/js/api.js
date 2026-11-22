/**
 * API client for Lilysana Education Mini App.
 * Automatically attaches Telegram initData for authentication.
 * Handles DEV_MODE when running outside Telegram.
 */

const API_BASE = window.location.port === '3000'
  ? 'http://localhost:8000'
  : window.location.origin;

const tg = window.Telegram?.WebApp;

function getInitData() {
  if (tg && tg.initData) return tg.initData;
  // Dev fallback: empty string triggers DEV_MODE on backend
  return '';
}

async function apiRequest(method, path, body = null) {
  const headers = {
    'Content-Type': 'application/json',
    'X-Init-Data': getInitData(),
    'ngrok-skip-browser-warning': 'true',
  };

  const opts = { method, headers };
  if (body !== null) opts.body = JSON.stringify(body);

  const resp = await fetch(`${API_BASE}${path}`, opts);

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new APIError(err.detail || 'Помилка запиту', resp.status);
  }

  const ct = resp.headers.get('content-type') || '';
  if (ct.includes('application/json')) return resp.json();
  return null;
}

class APIError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// ── API modules ──────────────────────────────────────────────────────────────

const API = {
  // User
  getMe: () => apiRequest('GET', '/api/users/me'),
  completeOnboarding: (data) => apiRequest('POST', '/api/users/me/onboarding', data),
  markWelcomeSeen: () => apiRequest('POST', '/api/users/me/welcome-seen'),
  getLimits: () => apiRequest('GET', '/api/users/me/limits'),
  updateLimits: (data) => apiRequest('PUT', '/api/users/me/limits', data),
  getSettings: () => apiRequest('GET', '/api/users/me/settings'),
  updateSettings: (data) => apiRequest('PUT', '/api/users/me/settings', data),
  getModules: () => apiRequest('GET', '/api/users/me/modules'),
  updateModules: (data) => apiRequest('PUT', '/api/users/me/modules', data),
  getBusySlots: () => apiRequest('GET', '/api/users/me/busy-slots'),
  createBusySlot: (data) => apiRequest('POST', '/api/users/me/busy-slots', data),
  deleteBusySlot: (id) => apiRequest('DELETE', `/api/users/me/busy-slots/${id}`),

  // NMT
  getSubjects: () => apiRequest('GET', '/api/nmt/subjects'),
  createSubject: (data) => apiRequest('POST', '/api/nmt/subjects', data),
  updateSubject: (id, data) => apiRequest('PUT', `/api/nmt/subjects/${id}`, data),
  getTopics: (subjectId) => apiRequest('GET', `/api/nmt/subjects/${subjectId}/topics`),
  createTopic: (subjectId, data) => apiRequest('POST', `/api/nmt/subjects/${subjectId}/topics`, data),
  getTests: (topicId) => apiRequest('GET', `/api/nmt/topics/${topicId}/tests`),
  createTest: (topicId, data) => apiRequest('POST', `/api/nmt/topics/${topicId}/tests`, data),
  addResult: (testId, data) => apiRequest('POST', `/api/nmt/tests/${testId}/results`, data),
  getTestHistory: (testId) => apiRequest('GET', `/api/nmt/tests/${testId}/results`),
  scheduleRepetition: (resultId, data) => apiRequest('POST', `/api/nmt/results/${resultId}/schedule-repetition`, data),
  getRepetitions: () => apiRequest('GET', '/api/nmt/repetitions'),
  completeRepetition: (repId) => apiRequest('PATCH', `/api/nmt/repetitions/${repId}/complete`),
  getOptionalSubjects: () => apiRequest('GET', '/api/optional-subjects'),

  // Courses
  getCourses: () => apiRequest('GET', '/api/courses'),
  createCourse: (data) => apiRequest('POST', '/api/courses', data),
  updateCourse: (id, data) => apiRequest('PUT', `/api/courses/${id}`, data),
  archiveCourse: (id) => apiRequest('DELETE', `/api/courses/${id}`),
  generateSchedule: (courseId) => apiRequest('POST', `/api/courses/${courseId}/generate-schedule`),
  getCourseProgress: (courseId) => apiRequest('GET', `/api/courses/${courseId}/progress`),
  setManualProgress: (courseId, data) => apiRequest('PUT', `/api/courses/${courseId}/manual-progress`, data),
  getCourseSessions: (courseId) => apiRequest('GET', `/api/courses/${courseId}/sessions`),
  completeSession: (sessionId, data) => apiRequest('PATCH', `/api/courses/sessions/${sessionId}/complete`, data || {}),
  rescheduleSession: (sessionId, newDate) => apiRequest('PATCH', `/api/courses/sessions/${sessionId}/reschedule?new_date=${encodeURIComponent(newDate)}`),
  markSessionMissed: (sessionId) => apiRequest('PATCH', `/api/courses/sessions/${sessionId}/mark-missed`),

  // Schedule
  getSchedule: (startDate, endDate) => {
    let path = '/api/schedule';
    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    if (params.toString()) path += '?' + params.toString();
    return apiRequest('GET', path);
  },

  // Statistics
  getStatistics: () => apiRequest('GET', '/api/statistics'),

  // Health
  health: () => apiRequest('GET', '/health'),
};

window.API = API;
window.APIError = APIError;
