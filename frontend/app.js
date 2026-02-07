// Madison Mentions - Frontend JavaScript

const searchSection = document.getElementById('search-section');
const form = document.getElementById('search-form');
const input = document.getElementById('reporter-name');
const searchBtn = document.getElementById('search-btn');
const loadingSection = document.getElementById('loading');
const errorSection = document.getElementById('error');
const errorMessage = document.getElementById('error-message');
const resultsSection = document.getElementById('results');
const noResultsSection = document.getElementById('no-results');
const loadingMessage = document.getElementById('loading-message');

// Results elements
const reporterTitle = document.getElementById('reporter-title');
const currentOutlet = document.getElementById('current-outlet');
const reporterTitleLine = document.getElementById('reporter-title-line');
const reporterBio = document.getElementById('reporter-bio');
const socialLinks = document.getElementById('social-links');
const queryDate = document.getElementById('query-date');
const lastUpdated = document.getElementById('last-updated');
const refreshBtn = document.getElementById('refresh-btn');
const outletChangeAlert = document.getElementById('outlet-change-alert');
const outletChangeNote = document.getElementById('outlet-change-note');
const articleCount = document.getElementById('article-count');
const articlesList = document.getElementById('articles-list');

// Import elements
const importNavBtn = document.getElementById('import-nav-btn');
const importUploadSection = document.getElementById('import-upload');
const importLoadingSection = document.getElementById('import-loading');
const importReviewSection = document.getElementById('import-review');
const importResultsSection = document.getElementById('import-results');
const importUploadError = document.getElementById('import-upload-error');
const importReviewError = document.getElementById('import-review-error');
const csvFileInput = document.getElementById('csv-file-input');
const csvChooseBtn = document.getElementById('csv-choose-btn');
const csvFilename = document.getElementById('csv-filename');
const csvAnalyzeBtn = document.getElementById('csv-analyze-btn');
const importSummary = document.getElementById('import-summary');
const importMappings = document.getElementById('import-mappings');
const importIssues = document.getElementById('import-issues');
const importDuplicates = document.getElementById('import-duplicates');
const importTable = document.getElementById('import-table');
const importSkipDupes = document.getElementById('import-skip-dupes');
const importCancelBtn = document.getElementById('import-cancel-btn');
const importConfirmBtn = document.getElementById('import-confirm-btn');
const importResultStats = document.getElementById('import-result-stats');
const importDoneBtn = document.getElementById('import-done-btn');

// State
let currentReporterName = null;
let importSessionId = null;
let importAnalysis = null;

// Track which sections are part of the import flow
const importSections = new Set([
    importUploadSection,
    importLoadingSection,
    importReviewSection,
    importResultsSection,
]);

function showSection(section) {
    loadingSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    noResultsSection.classList.add('hidden');
    refreshBtn.classList.add('hidden');
    importUploadSection.classList.add('hidden');
    importLoadingSection.classList.add('hidden');
    importReviewSection.classList.add('hidden');
    importResultsSection.classList.add('hidden');

    if (section) {
        section.classList.remove('hidden');
    }

    // Hide search section during import flow, show it otherwise
    const isImportScreen = section && importSections.has(section);
    searchSection.classList.toggle('hidden', isImportScreen);
}

function setLoading(isLoading) {
    searchBtn.disabled = isLoading;
    refreshBtn.disabled = isLoading;
    if (isLoading) {
        loadingMessage.textContent = 'Researching reporter...';
        showSection(loadingSection);
    }
}

function showError(message) {
    errorMessage.textContent = message;
    showSection(errorSection);
}

// Format date for display
function formatDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

// Format a timestamp to relative time like "Updated 3 days ago"
function formatTimeAgo(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHr / 24);

    if (diffSec < 60) return 'Updated just now';
    if (diffMin < 60) return `Updated ${diffMin}m ago`;
    if (diffHr < 24) return `Updated ${diffHr}h ago`;
    if (diffDays === 1) return 'Updated 1 day ago';
    if (diffDays < 30) return `Updated ${diffDays} days ago`;
    return `Updated ${formatDate(isoString.split('T')[0])}`;
}

// Render the dossier
function renderDossier(dossier) {
    if (!dossier.articles || dossier.articles.length === 0) {
        showSection(noResultsSection);
        return;
    }

    // Header
    reporterTitle.textContent = dossier.reporter_name;

    // Show last_updated instead of query date
    if (dossier.last_updated) {
        lastUpdated.textContent = formatTimeAgo(dossier.last_updated);
        queryDate.textContent = '';
    } else {
        queryDate.textContent = `Queried ${formatDate(dossier.query_date)}`;
        lastUpdated.textContent = '';
    }

    // Current outlet
    if (dossier.current_outlet) {
        currentOutlet.textContent = `Reporter at ${dossier.current_outlet}`;
    } else {
        currentOutlet.textContent = '';
    }

    // Reporter title/role from Perigon
    if (dossier.social_links && dossier.social_links.title) {
        reporterTitleLine.textContent = dossier.social_links.title;
    } else {
        reporterTitleLine.textContent = '';
    }

    // Social links
    renderSocialLinks(dossier.social_links, dossier.reporter_name);

    // Outlet change alert
    if (dossier.outlet_change_detected && dossier.outlet_change_note) {
        outletChangeNote.textContent = dossier.outlet_change_note;
        outletChangeAlert.classList.remove('hidden');
    } else {
        outletChangeAlert.classList.add('hidden');
    }

    // Reporter bio
    if (dossier.reporter_bio) {
        reporterBio.textContent = dossier.reporter_bio;
    } else {
        reporterBio.textContent = '';
    }

    // Article count
    articleCount.textContent = dossier.articles.length;

    // Articles list
    articlesList.innerHTML = dossier.articles
        .map(article => `
            <article class="article-card">
                <div class="article-header">
                    <a href="${sanitizeUrl(article.url)}"
                       target="_blank"
                       rel="noopener noreferrer"
                       class="article-headline">
                        ${escapeHtml(article.headline)}
                    </a>
                    <div class="article-meta">
                        <span class="article-outlet">${escapeHtml(article.outlet)}</span>
                        <span class="article-date">${formatDate(article.date)}</span>
                    </div>
                </div>
                ${article.summary ? `<p class="article-summary">${escapeHtml(article.summary)}</p>` : ''}
            </article>
        `)
        .join('');

    showSection(resultsSection);

    // Show refresh button
    refreshBtn.classList.remove('hidden');
    refreshBtn.disabled = false;
}

// HTML escaping for security
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// URL sanitization - only allow http/https
function sanitizeUrl(url) {
    if (!url) return '#';
    const trimmed = url.trim().toLowerCase();
    if (trimmed.startsWith('https://') || trimmed.startsWith('http://')) {
        return url;
    }
    return '#';
}

// SVG icons for social links
const socialIcons = {
    twitter: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
    linkedin: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>`,
    search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>`
};

// Render social links
function renderSocialLinks(links, reporterName) {
    const linksHtml = [];

    if (links) {
        // Twitter/X
        if (links.twitter_url) {
            linksHtml.push(`
                <a href="${sanitizeUrl(links.twitter_url)}" target="_blank" rel="noopener noreferrer" class="social-link">
                    ${socialIcons.twitter}
                    <span>@${escapeHtml(links.twitter_handle)}</span>
                </a>
            `);
        }

        // LinkedIn
        if (links.linkedin_url) {
            linksHtml.push(`
                <a href="${sanitizeUrl(links.linkedin_url)}" target="_blank" rel="noopener noreferrer" class="social-link">
                    ${socialIcons.linkedin}
                    <span>LinkedIn</span>
                </a>
            `);
        }
    }

    // Always show LinkedIn search fallback if no direct link
    if (!links || !links.linkedin_url) {
        const searchUrl = `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(reporterName)}`;
        linksHtml.push(`
            <a href="${searchUrl}" target="_blank" rel="noopener noreferrer" class="social-link">
                ${socialIcons.linkedin}
                <span>Search LinkedIn</span>
            </a>
        `);
    }

    // Always show Twitter search fallback if no direct link
    if (!links || !links.twitter_url) {
        const searchUrl = `https://twitter.com/search?q=${encodeURIComponent(reporterName)}&f=user`;
        linksHtml.push(`
            <a href="${searchUrl}" target="_blank" rel="noopener noreferrer" class="social-link">
                ${socialIcons.twitter}
                <span>Search X</span>
            </a>
        `);
    }

    socialLinks.innerHTML = linksHtml.join('');
}

// API call
async function searchReporter(name, refresh = false) {
    const encodedName = encodeURIComponent(name.trim());
    let url = `/api/reporter/${encodedName}`;
    if (refresh) {
        url += '?refresh=true';
    }
    const response = await fetch(url);

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Error: ${response.status}`);
    }

    return response.json();
}

// Refresh button handler
refreshBtn.addEventListener('click', async () => {
    if (!currentReporterName) return;

    refreshBtn.disabled = true;
    setLoading(true);

    try {
        const dossier = await searchReporter(currentReporterName, true);
        renderDossier(dossier);
    } catch (err) {
        showError(err.message || 'Failed to refresh reporter data. Please try again.');
    } finally {
        setLoading(false);
    }
});

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = input.value.trim();
    if (!name || name.length < 2) {
        showError('Please enter a reporter name (at least 2 characters)');
        return;
    }

    currentReporterName = name;
    setLoading(true);

    try {
        const dossier = await searchReporter(name);
        renderDossier(dossier);
    } catch (err) {
        showError(err.message || 'Failed to fetch reporter data. Please try again.');
    } finally {
        setLoading(false);
    }
});

// ==========================================================================
// CSV IMPORT FLOW
// ==========================================================================

// Import nav button → show upload section
importNavBtn.addEventListener('click', () => {
    showSection(importUploadSection);
});

// Choose file button → trigger hidden file input
csvChooseBtn.addEventListener('click', () => {
    csvFileInput.click();
});

// File selected → update display, enable analyze
csvFileInput.addEventListener('change', () => {
    const file = csvFileInput.files[0];
    if (file) {
        csvFilename.textContent = file.name;
        csvAnalyzeBtn.disabled = false;
    } else {
        csvFilename.textContent = '';
        csvAnalyzeBtn.disabled = true;
    }
});

// Analyze button → upload and get AI analysis
csvAnalyzeBtn.addEventListener('click', async () => {
    const file = csvFileInput.files[0];
    if (!file) return;

    csvAnalyzeBtn.disabled = true;
    importUploadError.classList.add('hidden');
    showSection(importLoadingSection);

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/import/analyze', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `Error: ${response.status}`);
        }

        const result = await response.json();
        importSessionId = result.session_id;
        importAnalysis = result;
        renderImportReview(result);
        showSection(importReviewSection);
    } catch (err) {
        // Return to upload section so the user can retry
        showSection(importUploadSection);
        csvAnalyzeBtn.disabled = false;
        importUploadError.textContent = err.message || 'Failed to analyze CSV file.';
        importUploadError.classList.remove('hidden');
    }
});

// Render import review screen
function renderImportReview(result) {
    const analysis = result.analysis;
    const confidence = analysis.confidence || 'medium';

    // Summary
    importSummary.innerHTML = `
        <div><strong>${escapeHtml(result.filename)}</strong> &mdash; ${result.total_rows} rows, ${result.headers.length} columns</div>
        <div>AI Confidence: <span class="import-confidence ${confidence}">${confidence}</span></div>
    `;

    // Column mapping dropdowns
    const fields = ['name', 'outlet', 'bio', 'twitter', 'linkedin'];
    const mapping = analysis.column_mapping || {};
    importMappings.innerHTML = fields.map(field => {
        const options = result.headers.map(h =>
            `<option value="${escapeHtml(h)}" ${mapping[field] === h ? 'selected' : ''}>${escapeHtml(h)}</option>`
        ).join('');
        return `
            <div class="mapping-row">
                <span class="mapping-label">${field}</span>
                <select class="mapping-select" data-field="${field}">
                    <option value="">-- Not mapped --</option>
                    ${options}
                </select>
            </div>
        `;
    }).join('');

    // Issues + normalizations
    const items = [
        ...(analysis.issues || []),
        ...(analysis.normalizations || []),
    ];
    if (items.length > 0) {
        importIssues.innerHTML = '<ul>' + items.map(i => `<li>${escapeHtml(i)}</li>`).join('') + '</ul>';
    } else {
        importIssues.innerHTML = '';
    }

    // Duplicates
    if (result.duplicates && result.duplicates.length > 0) {
        importDuplicates.innerHTML = '<ul>' +
            result.duplicates.map(d => `<li>${escapeHtml(d)} — already exists</li>`).join('') +
            '</ul>';
    } else {
        importDuplicates.innerHTML = '';
    }

    // Sample data table
    const sampleRows = result.sample_rows || [];
    if (sampleRows.length > 0) {
        const headerRow = result.headers.map(h => `<th>${escapeHtml(h)}</th>`).join('');
        const bodyRows = sampleRows.map(row =>
            '<tr>' + result.headers.map(h => `<td>${escapeHtml(row[h] || '')}</td>`).join('') + '</tr>'
        ).join('');
        importTable.innerHTML = `<thead><tr>${headerRow}</tr></thead><tbody>${bodyRows}</tbody>`;
    } else {
        importTable.innerHTML = '';
    }
}

// Cancel → reset and go back
importCancelBtn.addEventListener('click', () => {
    resetImportState();
    showSection(null);
});

// Confirm → apply mapping and import
importConfirmBtn.addEventListener('click', async () => {
    if (!importSessionId) return;

    importConfirmBtn.disabled = true;
    importReviewError.classList.add('hidden');

    // Gather mapping from dropdowns
    const columnMapping = {};
    importMappings.querySelectorAll('.mapping-select').forEach(select => {
        const field = select.dataset.field;
        const value = select.value;
        columnMapping[field] = value || null;
    });

    if (!columnMapping.name) {
        importReviewError.textContent = 'Name column mapping is required.';
        importReviewError.classList.remove('hidden');
        importConfirmBtn.disabled = false;
        return;
    }

    showSection(importLoadingSection);

    try {
        const response = await fetch('/api/import/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: importSessionId,
                column_mapping: columnMapping,
                skip_duplicates: importSkipDupes.checked,
            }),
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `Error: ${response.status}`);
        }

        const result = await response.json();
        renderImportResults(result);
        showSection(importResultsSection);
    } catch (err) {
        // Return to review section so the user can retry
        showSection(importReviewSection);
        importReviewError.textContent = err.message || 'Failed to import reporters.';
        importReviewError.classList.remove('hidden');
    } finally {
        importConfirmBtn.disabled = false;
    }
});

// Render import results
function renderImportResults(result) {
    const stats = [
        { label: 'Imported', count: result.imported, cls: '' },
        { label: 'Skipped', count: result.skipped, cls: '' },
        { label: 'Errors', count: result.errors, cls: result.errors > 0 ? 'result-errors' : '' },
    ];

    importResultStats.innerHTML = stats.map(s => `
        <div class="result-stat ${s.cls}">
            <span class="result-count">${s.count}</span>
            <span class="result-label">${s.label}</span>
        </div>
    `).join('');
}

// Done → reset and return
importDoneBtn.addEventListener('click', () => {
    resetImportState();
    showSection(null);
});

function resetImportState() {
    importSessionId = null;
    importAnalysis = null;
    csvFileInput.value = '';
    csvFilename.textContent = '';
    csvAnalyzeBtn.disabled = true;
    importUploadError.classList.add('hidden');
    importReviewError.classList.add('hidden');
}

// Focus input on load
input.focus();
