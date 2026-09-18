/**
 * ATS Resume Analyzer v2 — Main Application Logic
 *
 * Handles: file upload, form submission, results rendering,
 * theme toggle, toast notifications, loading states.
 */

document.addEventListener('DOMContentLoaded', () => {
  // ═══════════════════════════════════════════
  // DOM Elements
  // ═══════════════════════════════════════════
  const dropZone       = document.getElementById('drop-zone');
  const fileInput      = document.getElementById('file-input');
  const fileInfo       = document.getElementById('file-info');
  const fileName       = document.getElementById('file-name');
  const fileSize       = document.getElementById('file-size');
  const fileRemove     = document.getElementById('file-remove');
  const jdInput        = document.getElementById('jd-input');
  const skillsInput    = document.getElementById('skills-input');
  const expInput       = document.getElementById('exp-input');
  const analyzeBtn     = document.getElementById('analyze-btn');
  const uploadSection  = document.getElementById('upload-section');
  const loader         = document.getElementById('loader');
  const resultsSection = document.getElementById('results-section');
  const themeToggle    = document.getElementById('theme-toggle');
  const apiStatus      = document.getElementById('api-status');

  let selectedFile = null;

  // ═══════════════════════════════════════════
  // Theme Toggle
  // ═══════════════════════════════════════════
  const savedTheme = localStorage.getItem('ats-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcons(savedTheme);

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('ats-theme', next);
    updateThemeIcons(next);
  });

  function updateThemeIcons(theme) {
    const moon = document.getElementById('theme-icon-moon');
    const sun  = document.getElementById('theme-icon-sun');
    if (theme === 'dark') {
      moon.classList.remove('hidden');
      sun.classList.add('hidden');
    } else {
      moon.classList.add('hidden');
      sun.classList.remove('hidden');
    }
  }

  // ═══════════════════════════════════════════
  // Health Check
  // ═══════════════════════════════════════════
  API.healthCheck()
    .then(() => { apiStatus.classList.add('online'); apiStatus.classList.remove('offline'); })
    .catch(() => { apiStatus.classList.add('offline'); apiStatus.classList.remove('online'); });

  // ═══════════════════════════════════════════
  // File Upload — Drag & Drop + Click
  // ═══════════════════════════════════════════
  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileSelect(files[0]);
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
  });

  fileRemove.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    dropZone.classList.remove('hidden');
    updateAnalyzeBtn();
  });

  function handleFileSelect(file) {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];

    if (!validTypes.includes(file.type) && !file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
      showToast('Unsupported file type. Upload a PDF or DOCX.', 'error');
      return;
    }

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      showToast(`File too large (${formatBytes(file.size)}). Maximum is 10 MB.`, 'error');
      return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    fileInfo.classList.remove('hidden');
    dropZone.classList.add('hidden');
    updateAnalyzeBtn();
  }

  // ═══════════════════════════════════════════
  // Form Validation
  // ═══════════════════════════════════════════
  jdInput.addEventListener('input', updateAnalyzeBtn);

  function updateAnalyzeBtn() {
    const hasFile = selectedFile !== null;
    const hasJD   = jdInput.value.trim().length > 0;
    analyzeBtn.disabled = !(hasFile && hasJD);
  }

  // ═══════════════════════════════════════════
  // Analyze — Submit
  // ═══════════════════════════════════════════
  analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile || !jdInput.value.trim()) return;

    // Show loader, hide form
    uploadSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    loader.classList.add('active');

    // Animate loader steps
    const steps = ['extract', 'parse', 'score', 'context'];
    let currentStep = 0;

    function advanceStep() {
      if (currentStep > 0) {
        document.getElementById(`step-${steps[currentStep - 1]}`).classList.remove('active');
        document.getElementById(`step-${steps[currentStep - 1]}`).classList.add('done');
        document.getElementById(`label-${steps[currentStep - 1]}`).classList.remove('active');
        document.getElementById(`label-${steps[currentStep - 1]}`).classList.add('done');
      }
      if (currentStep < steps.length) {
        document.getElementById(`step-${steps[currentStep]}`).classList.add('active');
        document.getElementById(`label-${steps[currentStep]}`).classList.add('active');
        currentStep++;
      }
    }

    advanceStep();
    const stepInterval = setInterval(advanceStep, 800);

    try {
      const result = await API.analyzeResume(
        selectedFile,
        jdInput.value.trim(),
        skillsInput.value.trim(),
        parseInt(expInput.value) || 36,
      );

      clearInterval(stepInterval);
      // Mark all steps done
      steps.forEach(s => {
        document.getElementById(`step-${s}`).classList.remove('active');
        document.getElementById(`step-${s}`).classList.add('done');
        document.getElementById(`label-${s}`).classList.remove('active');
        document.getElementById(`label-${s}`).classList.add('done');
      });

      setTimeout(() => {
        loader.classList.remove('active');
        renderResults(result);
        showToast(`Analysis complete (${(result.processing_time_ms / 1000).toFixed(1)}s)`, 'success');
      }, 400);

    } catch (err) {
      clearInterval(stepInterval);
      loader.classList.remove('active');
      uploadSection.classList.remove('hidden');
      showToast(err.message, 'error');

      // Reset loader steps
      steps.forEach(s => {
        const dot = document.getElementById(`step-${s}`);
        const label = document.getElementById(`label-${s}`);
        dot.classList.remove('active', 'done');
        label.classList.remove('active', 'done');
      });
    }
  });

  // ═══════════════════════════════════════════
  // Results Rendering
  // ═══════════════════════════════════════════
  function renderResults(data) {
    const scoreColor = getScoreColor(data.total_score);
    const scoreLabel = getScoreLabel(data.total_score);
    const circumference = 2 * Math.PI * 72;
    const offset = circumference - (data.total_score / 100) * circumference;
    const pr = data.parsed_resume;

    resultsSection.innerHTML = `
      ${data.manual_review_recommended ? `
        <div class="review-banner">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Manual review recommended — extraction or parsing had low confidence.
        </div>
      ` : ''}

      <!-- ═══ Top Row: Score Ring + Breakdown ═══ -->
      <div class="results-grid">
        <!-- Score Ring -->
        <div class="card score-ring-container">
          <div class="score-ring-wrapper">
            <svg viewBox="0 0 160 160">
              <circle class="score-ring-track" cx="80" cy="80" r="72"/>
              <circle class="score-ring-fill" cx="80" cy="80" r="72"
                stroke="${scoreColor}"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${circumference}"
                id="score-ring-circle"/>
            </svg>
            <div class="score-ring-text">
              <div class="score-number" style="color: ${scoreColor}" id="score-counter">0</div>
              <div class="score-denominator">/ 100</div>
            </div>
          </div>
          <div class="score-label-badge" style="background: ${scoreColor}15; color: ${scoreColor}; border: 1px solid ${scoreColor}40; padding: 0.3rem 1rem; border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--font-bold); margin-top: var(--space-3); letter-spacing: 0.05em;">
            ${scoreLabel}
          </div>
          <div style="margin-top: var(--space-4); text-align: center;">
            <div class="text-sm" style="font-weight: var(--font-semibold); color: var(--text-primary);">${data.candidate_name}</div>
            <div class="text-xs text-secondary mono" style="margin-top: var(--space-1);">Config ${data.scoring_config_version} · ${data.processing_time_ms}ms</div>
          </div>
        </div>

        <!-- Score Breakdown + Skills -->
        <div class="card">
          <div class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            Score Breakdown
          </div>

          <div class="breakdown-bar">
            <div class="breakdown-bar-header">
              <span class="breakdown-bar-label">Semantic Skill Match</span>
              <span class="breakdown-bar-value">${data.semantic_skill_match.toFixed(1)} / ${data.skill_weight}</span>
            </div>
            <div class="breakdown-bar-track">
              <div class="breakdown-bar-fill bar-skill" data-width="${(data.semantic_skill_match / data.skill_weight * 100).toFixed(1)}"></div>
            </div>
          </div>

          <div class="breakdown-bar">
            <div class="breakdown-bar-header">
              <span class="breakdown-bar-label">Experience Longevity</span>
              <span class="breakdown-bar-value">${data.experience_longevity.toFixed(1)} / ${data.experience_weight}</span>
            </div>
            <div class="breakdown-bar-track">
              <div class="breakdown-bar-fill bar-exp" data-width="${(data.experience_longevity / data.experience_weight * 100).toFixed(1)}"></div>
            </div>
          </div>

          <div class="breakdown-bar">
            <div class="breakdown-bar-header">
              <span class="breakdown-bar-label">Contextual AI Fit</span>
              <span class="breakdown-bar-value">${data.context_alignment.toFixed(1)} / ${data.context_weight}</span>
            </div>
            <div class="breakdown-bar-track">
              <div class="breakdown-bar-fill bar-context" data-width="${(data.context_alignment / data.context_weight * 100).toFixed(1)}"></div>
            </div>
          </div>

          <!-- Matched / Missing / Unverified Skills -->
          <div class="skills-section">
            ${data.matched_skills.length > 0 ? `
              <div class="skills-group">
                <div class="skills-group-title">Matched Skills</div>
                <div class="skills-tags">
                  ${data.matched_skills.map(s => `<span class="badge badge-success">✓ ${s}</span>`).join('')}
                </div>
              </div>
            ` : ''}
            ${data.missing_skills.length > 0 ? `
              <div class="skills-group">
                <div class="skills-group-title">Missing Skills</div>
                <div class="skills-tags">
                  ${data.missing_skills.map(s => `<span class="badge badge-error">✗ ${s}</span>`).join('')}
                </div>
              </div>
            ` : ''}
          </div>
        </div>
      </div>

      <!-- ═══ Verified vs Unverified Skills ═══ -->
      ${(data.verified_skills.length > 0 || data.unverified_skills.length > 0) ? `
        <div class="grid-2" style="margin-top: var(--space-6);">
          <div class="card">
            <div class="card-title" style="color: var(--color-success);">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              Verified Skills (${data.verified_skills.length})
            </div>
            <div class="skills-tags">
              ${data.verified_skills.length > 0 
                ? data.verified_skills.map(s => `<span class="badge badge-success">✓ ${s}</span>`).join('')
                : '<span class="text-xs text-secondary">No skills verified against resume text</span>'}
            </div>
          </div>
          <div class="card">
            <div class="card-title" style="color: var(--color-warning);">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              Unverified Skills (${data.unverified_skills.length})
            </div>
            <div class="skills-tags">
              ${data.unverified_skills.length > 0
                ? data.unverified_skills.map(s => `<span class="badge badge-warning">⚠ ${s}</span>`).join('')
                : '<span class="text-xs text-secondary">All skills verified</span>'}
            </div>
          </div>
        </div>
      ` : ''}

      <!-- ═══ Experience Timeline ═══ -->
      ${pr.experience.length > 0 ? `
        <div class="card" style="margin-top: var(--space-6);">
          <div class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
            Experience (${data.total_experience_months} months total)
          </div>
          <div class="timeline">
            ${pr.experience.map(exp => `
              <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                  <div class="timeline-title">${exp.role} at ${exp.company}</div>
                  <div class="timeline-subtitle">${exp.duration_months} months</div>
                  ${exp.responsibilities.length > 0 ? `
                    <ul class="timeline-bullets">
                      ${exp.responsibilities.slice(0, 5).map(r => `<li>${r}</li>`).join('')}
                    </ul>
                  ` : ''}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <!-- ═══ Education & Certifications ═══ -->
      ${(pr.education.length > 0 || pr.certifications.length > 0) ? `
        <div class="grid-2" style="margin-top: var(--space-6);">
          ${pr.education.length > 0 ? `
            <div class="card">
              <div class="card-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 1.1 2.7 3 6 3s6-1.9 6-3v-5"/></svg>
                Education
              </div>
              <div class="education-list">
                ${pr.education.map(e => `
                  <div class="edu-item">
                    <div class="edu-dot"></div>
                    <span class="text-sm">${e}</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
          ${pr.certifications.length > 0 ? `
            <div class="card">
              <div class="card-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>
                Certifications
              </div>
              <div class="education-list">
                ${pr.certifications.map(c => `
                  <div class="edu-item">
                    <div class="edu-dot" style="background: var(--accent-secondary);"></div>
                    <span class="text-sm">${c}</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      ` : ''}

      <!-- ═══ Projects ═══ -->
      ${pr.projects.length > 0 ? `
        <div class="card" style="margin-top: var(--space-6);">
          <div class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            Projects (${pr.projects.length})
          </div>
          <div class="grid-2">
            ${pr.projects.map(p => `
              <div class="project-card">
                <div class="project-name">${p.name}</div>
                ${p.tech_stack.length > 0 ? `
                  <div class="skills-tags" style="margin-top: var(--space-2);">
                    ${p.tech_stack.map(t => `<span class="badge badge-info">${t}</span>`).join('')}
                  </div>
                ` : ''}
                ${p.description ? `<p class="text-sm text-secondary" style="margin-top: var(--space-2); line-height: 1.6;">${p.description}</p>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      <!-- ═══ All Parsed Skills ═══ -->
      ${pr.skills.length > 0 ? `
        <div class="card" style="margin-top: var(--space-6);">
          <div class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            All Parsed Skills (${pr.skills.length})
          </div>
          <div class="skills-tags">
            ${pr.skills.map(s => `<span class="badge badge-neutral">${s}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      <!-- ═══ AI Justification ═══ -->
      ${data.context_justification ? `
        <div class="card" style="margin-top: var(--space-6);">
          <div class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            AI Contextual Justification
          </div>
          <div class="justification-text">${data.context_justification}</div>
        </div>
      ` : ''}

      <!-- ═══ Metadata Chips ═══ -->
      <div class="metadata-chips" style="margin-top: var(--space-6);">
        <span class="badge badge-info">Tier ${data.extraction_tier_used}</span>
        <span class="badge badge-neutral mono">${(data.processing_time_ms / 1000).toFixed(1)}s</span>
        <span class="badge badge-neutral mono">${data.llm_parse_attempts} attempt${data.llm_parse_attempts !== 1 ? 's' : ''}</span>
        <span class="badge badge-neutral">Config ${data.scoring_config_version}</span>
        ${data.calibration_applied ? '<span class="badge badge-info">⚡ Cached</span>' : ''}
        ${data.used_regex_fallback ? '<span class="badge badge-warning">Regex Fallback</span>' : ''}
        ${data.difficult_layout_detected ? '<span class="badge badge-warning">Complex Layout</span>' : ''}
      </div>

      <!-- ═══ Feedback Bar ═══ -->
      <div class="feedback-bar" id="feedback-bar">
        <div class="feedback-question">Was this score accurate?</div>
        <div class="feedback-buttons">
          <button class="feedback-btn" data-type="accurate">✓ Accurate</button>
          <button class="feedback-btn" data-type="too_high">↑ Too High</button>
          <button class="feedback-btn" data-type="too_low">↓ Too Low</button>
          <button class="feedback-btn" data-type="inaccurate">✗ Inaccurate</button>
        </div>
      </div>

      <!-- ═══ Actions ═══ -->
      <div style="margin-top: var(--space-6); display: flex; gap: var(--space-3); flex-wrap: wrap;">
        <button class="btn btn-secondary" id="export-json-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Export JSON
        </button>
        <button class="btn btn-primary" id="analyze-another-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          Analyze Another
        </button>
      </div>
    `;

    resultsSection.classList.remove('hidden');

    // Animate score ring
    requestAnimationFrame(() => {
      const ring = document.getElementById('score-ring-circle');
      if (ring) ring.style.strokeDashoffset = offset;

      // Animate breakdown bars
      document.querySelectorAll('.breakdown-bar-fill').forEach(bar => {
        const width = bar.getAttribute('data-width');
        bar.style.width = `${Math.min(parseFloat(width), 100)}%`;
      });

      // Animate score counter
      animateCounter('score-counter', data.total_score);
    });

    // Bind feedback buttons
    document.querySelectorAll('.feedback-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const type = btn.getAttribute('data-type');
        try {
          await API.submitFeedback(data.id, type);
          document.querySelectorAll('.feedback-btn').forEach(b => {
            b.disabled = true;
            b.classList.remove('selected');
          });
          btn.classList.add('selected');
          document.querySelector('.feedback-question').textContent = 'Thank you for your feedback!';
          showToast('Feedback submitted', 'success');
        } catch (err) {
          showToast(`Feedback failed: ${err.message}`, 'error');
        }
      });
    });

    // Bind export JSON
    document.getElementById('export-json-btn').addEventListener('click', () => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${data.candidate_name.replace(/\s+/g, '_')}_analysis.json`;
      a.click();
      URL.revokeObjectURL(url);
    });

    // Bind analyze another
    document.getElementById('analyze-another-btn').addEventListener('click', () => {
      resultsSection.classList.add('hidden');
      resultsSection.innerHTML = '';
      uploadSection.classList.remove('hidden');
      selectedFile = null;
      fileInput.value = '';
      fileInfo.classList.add('hidden');
      dropZone.classList.remove('hidden');
      jdInput.value = '';
      skillsInput.value = '';
      expInput.value = '36';
      updateAnalyzeBtn();
    });
  }

  // ═══════════════════════════════════════════
  // Utilities
  // ═══════════════════════════════════════════

  function getScoreColor(score) {
    if (score >= 90) return 'var(--score-excellent)';
    if (score >= 70) return 'var(--score-high)';
    if (score >= 40) return 'var(--score-medium)';
    return 'var(--score-low)';
  }

  function getScoreLabel(score) {
    if (score >= 90) return 'EXCELLENT FIT';
    if (score >= 70) return 'STRONG FIT';
    if (score >= 40) return 'MODERATE FIT';
    return 'WEAK FIT';
  }

  function animateCounter(elementId, target) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const duration = 1600;
    const start = performance.now();

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = (eased * target).toFixed(1);
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  }

  /**
   * Show a toast notification.
   * @param {string} message
   * @param {'success'|'error'|'warning'} type
   */
  function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
      success: '✓',
      error: '✗',
      warning: '⚠',
    };

    toast.innerHTML = `
      <span style="font-size: var(--text-lg);">${icons[type] || ''}</span>
      <span class="text-sm">${message}</span>
      <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto-dismiss
    const delay = type === 'error' ? 7000 : 5000;
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all var(--duration-fast) var(--ease-out)';
      setTimeout(() => toast.remove(), 200);
    }, delay);
  }
});
