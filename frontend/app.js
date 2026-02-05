// Madison Mentions - Frontend JavaScript

const form = document.getElementById('search-form');
const input = document.getElementById('reporter-name');
const searchBtn = document.getElementById('search-btn');
const loadingSection = document.getElementById('loading');
const errorSection = document.getElementById('error');
const errorMessage = document.getElementById('error-message');
const resultsSection = document.getElementById('results');
const noResultsSection = document.getElementById('no-results');

// Results elements
const reporterTitle = document.getElementById('reporter-title');
const beatsSummary = document.getElementById('beats-summary');
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

    // Beats summary in header
    if (dossier.primary_beats && dossier.primary_beats.length > 0) {
        const topBeats = dossier.primary_beats.slice(0, 3).map(b => b.beat);
        beatsSummary.innerHTML = `<strong>Covers:</strong> ${topBeats.map(b => escapeHtml(b)).join(', ')}`;
    } else {
        beatsSummary.innerHTML = '';
    }

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
                    <a href="${escapeHtml(article.url)}"
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
