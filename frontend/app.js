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

    if (section) {
        section.classList.remove('hidden');
    }
}

function setLoading(isLoading) {
    searchBtn.disabled = isLoading;
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

// API call
async function searchReporter(name) {
    const encodedName = encodeURIComponent(name.trim());
    const response = await fetch(`/api/reporter/${encodedName}`);

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Error: ${response.status}`);
    }

    return response.json();
}

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = input.value.trim();
    if (!name || name.length < 2) {
        showError('Please enter a reporter name (at least 2 characters)');
        return;
    }

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

// Focus input on load
input.focus();
