/**
 * ATS Resume Analyzer v2 — API Client
 *
 * Centralized API communication layer.
 * All backend calls go through this file.
 */

const API = (() => {
  const BASE_URL = window.location.origin;
  let API_KEY = 'dev-api-key-change-in-production'; // fallback default

  // Fetch the real API key from the backend at startup
  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/config`);
      if (res.ok) {
        const cfg = await res.json();
        if (cfg.api_key) API_KEY = cfg.api_key;
      }
    } catch (e) {
      console.warn('Could not fetch API config, using default key');
    }
  })();

  /**
   * Make an authenticated request to the backend.
   * @param {string} path - API path (e.g., '/api/v1/analyze')
   * @param {object} options - fetch options
   * @returns {Promise<Response>}
   */
  async function request(path, options = {}) {
    const url = `${BASE_URL}${path}`;
    const headers = {
      'X-API-Key': API_KEY,
      ...(options.headers || {}),
    };

    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Check backend health (public — no auth).
   */
  async function healthCheck() {
    const response = await fetch(`${BASE_URL}/health`);
    return response.json();
  }

  /**
   * Analyze a resume against a job description.
   * @param {File} file - PDF or DOCX file
   * @param {string} jobDescription - JD text
   * @param {string} requiredSkills - Comma-separated skills
   * @param {number} experienceTarget - Target months
   * @returns {Promise<object>} AnalysisResult
   */
  async function analyzeResume(file, jobDescription, requiredSkills, experienceTarget) {
    const formData = new FormData();
    formData.append('resume', file);
    formData.append('job_description', jobDescription);
    formData.append('required_skills', requiredSkills);
    formData.append('experience_target_months', experienceTarget.toString());

    return request('/api/v1/analyze', {
      method: 'POST',
      body: formData,
    });
  }

  /**
   * Get analysis history.
   */
  async function getHistory(page = 1, limit = 20, name = '') {
    const params = new URLSearchParams({ page, limit, name });
    return request(`/api/v1/history?${params}`);
  }

  /**
   * Get analysis detail by ID.
   */
  async function getAnalysis(id) {
    return request(`/api/v1/analyses/${id}`);
  }

  /**
   * Submit recruiter feedback.
   */
  async function submitFeedback(analysisId, feedbackType, reason = '') {
    return request('/api/v1/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_id: analysisId,
        feedback_type: feedbackType,
        reason,
      }),
    });
  }

  /**
   * Get analytics summary.
   */
  async function getAnalyticsSummary() {
    return request('/api/v1/analytics/summary');
  }

  /**
   * Compare two analyses side-by-side.
   * @param {string} idA - First analysis UUID
   * @param {string} idB - Second analysis UUID
   */
  async function compareAnalyses(idA, idB) {
    return request(`/api/v1/compare?a=${idA}&b=${idB}`);
  }

  return {
    healthCheck,
    analyzeResume,
    getHistory,
    getAnalysis,
    compareAnalyses,
    submitFeedback,
    getAnalyticsSummary,
  };
})();
