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

// State
let currentReporterName = null;

// State management
function showSection(section) {
    loadingSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    noResultsSection.classList.add('hidden');
    refreshBtn.classList.add('hidden');

    if (section) {
        section.classList.remove('hidden');
    }
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

// Focus input on load
input.focus();
