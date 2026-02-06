// Madison Mentions - Frontend JavaScript

const form = document.getElementById('search-form');
const input = document.getElementById('reporter-name');
const searchBtn = document.getElementById('search-btn');
const loadingSection = document.getElementById('loading');
const errorSection = document.getElementById('error');
const errorMessage = document.getElementById('error-message');
const resultsSection = document.getElementById('results');
const noResultsSection = document.getElementById('no-results');
const loadingMessage = document.getElementById('loading-message');

// Beat search elements
const beatResultsSection = document.getElementById('beat-results');
const noBeatResultsSection = document.getElementById('no-beat-results');
const beatTopic = document.getElementById('beat-topic');
const beatCount = document.getElementById('beat-count');
const journalistsList = document.getElementById('journalists-list');
const tabBtns = document.querySelectorAll('.tab-btn');

// Search mode: 'reporter' or 'beat'
let searchMode = 'reporter';

// Results elements
const reporterTitle = document.getElementById('reporter-title');
const reporterTitleLine = document.getElementById('reporter-title-line');
const beatsSummary = document.getElementById('beats-summary');
const socialLinks = document.getElementById('social-links');
const queryDate = document.getElementById('query-date');
const outletChangeAlert = document.getElementById('outlet-change-alert');
const outletChangeNote = document.getElementById('outlet-change-note');
const beatBadges = document.getElementById('beat-badges');
const outletBadges = document.getElementById('outlet-badges');
const articleCount = document.getElementById('article-count');
const articlesList = document.getElementById('articles-list');

// State management
function showSection(section) {
    loadingSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    noResultsSection.classList.add('hidden');
    beatResultsSection.classList.add('hidden');
    noBeatResultsSection.classList.add('hidden');

    if (section) {
        section.classList.remove('hidden');
    }
}

// Tab switching
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        searchMode = btn.dataset.mode;

        // Update placeholder
        if (searchMode === 'beat') {
            input.placeholder = 'Search by topic (e.g., Politics, Technology)...';
        } else {
            input.placeholder = 'Search reporters...';
        }

        // Clear results
        showSection(null);
    });
});

function setLoading(isLoading) {
    searchBtn.disabled = isLoading;
    if (isLoading) {
        loadingMessage.textContent = searchMode === 'beat'
            ? 'Finding journalists...'
            : 'Researching reporter...';
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

// Render the dossier
function renderDossier(dossier) {
    if (!dossier.articles || dossier.articles.length === 0) {
        showSection(noResultsSection);
        return;
    }

    // Header
    reporterTitle.textContent = dossier.reporter_name;
    queryDate.textContent = `Queried ${formatDate(dossier.query_date)}`;

    // Reporter title/role
    if (dossier.social_links && dossier.social_links.title) {
        reporterTitleLine.textContent = dossier.social_links.title;
    } else {
        reporterTitleLine.textContent = '';
    }

    // Beats summary in header
    if (dossier.primary_beats && dossier.primary_beats.length > 0) {
        const topBeats = dossier.primary_beats.slice(0, 3).map(b => b.beat);
        beatsSummary.innerHTML = `<strong>Covers:</strong> ${topBeats.map(b => escapeHtml(b)).join(', ')}`;
    } else {
        beatsSummary.innerHTML = '';
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

    // Beat badges
    if (dossier.primary_beats && dossier.primary_beats.length > 0) {
        beatBadges.innerHTML = dossier.primary_beats
            .slice(0, 8)  // Show top 8 beats
            .map(b => `
                <div class="beat-badge">
                    <span class="beat-name">${escapeHtml(b.beat)}</span>
                    <span class="beat-count">${b.count}</span>
                </div>
            `)
            .join('');
    } else {
        beatBadges.innerHTML = '<span class="no-beats">No beat data available</span>';
    }

    // Outlet badges
    outletBadges.innerHTML = dossier.outlet_history
        .map(oh => `
            <div class="outlet-badge">
                <span class="outlet-name">${escapeHtml(oh.outlet)}</span>
                <span class="outlet-count">${oh.count}</span>
            </div>
        `)
        .join('');

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

// API call - Reporter search
async function searchReporter(name) {
    const encodedName = encodeURIComponent(name.trim());
    const response = await fetch(`/api/reporter/${encodedName}`);

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Error: ${response.status}`);
    }

    return response.json();
}

// API call - Beat/topic search
async function searchByBeat(topic) {
    const encodedTopic = encodeURIComponent(topic.trim());
    const response = await fetch(`/api/journalists/search?topic=${encodedTopic}&limit=20`);

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Error: ${response.status}`);
    }

    return response.json();
}

// Render journalist search results
function renderJournalistResults(data) {
    if (!data.journalists || data.journalists.length === 0) {
        showSection(noBeatResultsSection);
        return;
    }

    beatTopic.textContent = data.topic;
    beatCount.textContent = `${data.total_results} journalists found`;

    journalistsList.innerHTML = data.journalists.map(j => `
        <div class="journalist-card">
            <div class="journalist-header">
                <span class="journalist-name">${escapeHtml(j.name)}</span>
                ${j.title ? `<span class="journalist-title">${escapeHtml(j.title)}</span>` : ''}
            </div>
            ${j.outlets && j.outlets.length > 0 ? `
                <div class="journalist-outlets">
                    ${j.outlets.map(o => `<span class="outlet-tag">${escapeHtml(o)}</span>`).join('')}
                </div>
            ` : ''}
            <div class="journalist-links">
                ${j.twitter_url ? `
                    <a href="${sanitizeUrl(j.twitter_url)}" target="_blank" rel="noopener noreferrer" class="social-link small">
                        ${socialIcons.twitter}
                        <span>@${escapeHtml(j.twitter_handle)}</span>
                    </a>
                ` : ''}
                ${j.linkedin_url ? `
                    <a href="${sanitizeUrl(j.linkedin_url)}" target="_blank" rel="noopener noreferrer" class="social-link small">
                        ${socialIcons.linkedin}
                        <span>LinkedIn</span>
                    </a>
                ` : ''}
                <button class="view-dossier-btn" data-reporter="${escapeHtml(j.name)}">View Dossier</button>
            </div>
            ${j.article_count > 0 ? `<span class="article-count-badge">${j.article_count} articles</span>` : ''}
        </div>
    `).join('');

    showSection(beatResultsSection);
}

// Switch to reporter view from beat search
function viewDossier(name) {
    // Switch to reporter mode
    tabBtns.forEach(b => b.classList.remove('active'));
    tabBtns[0].classList.add('active');
    searchMode = 'reporter';
    input.placeholder = 'Search reporters...';
    input.value = name;
    form.dispatchEvent(new Event('submit'));
}

// Event delegation for View Dossier buttons
journalistsList.addEventListener('click', (e) => {
    const btn = e.target.closest('.view-dossier-btn');
    if (btn) {
        const reporterName = btn.dataset.reporter;
        if (reporterName) {
            viewDossier(reporterName);
        }
    }
});

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const query = input.value.trim();
    if (!query || query.length < 2) {
        showError(searchMode === 'beat'
            ? 'Please enter a topic (at least 2 characters)'
            : 'Please enter a reporter name (at least 2 characters)');
        return;
    }

    setLoading(true);

    try {
        if (searchMode === 'beat') {
            const results = await searchByBeat(query);
            renderJournalistResults(results);
        } else {
            const dossier = await searchReporter(query);
            renderDossier(dossier);
        }
    } catch (err) {
        showError(err.message || 'Failed to fetch data. Please try again.');
    } finally {
        setLoading(false);
    }
});

// Focus input on load
input.focus();
