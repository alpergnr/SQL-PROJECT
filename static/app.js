/* ═══════════════════════════════════════════════════════════════════════
   NJOY EMLAK — SPA Application Logic
   ═══════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    const API = {
        listings: "/api/listings",
        search: "/api/search",
        stats: "/api/stats",
        benchmark: "/api/benchmark",
        meta: "/api/meta",
    };

    // ── DOM Cache ────────────────────────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        navLinks: $$("#nav-links .nav-link"),
        mobileToggle: $("#nav-mobile-toggle"),
        navLinksContainer: $("#nav-links"),
        panels: $$(".tab-panel"),
        // listings
        listingsGrid: $("#listings-grid"),
        listingsSort: $("#listings-sort"),
        listingsLimit: $("#listings-limit"),
        // search
        searchForm: $("#search-form"),
        searchGrid: $("#search-grid"),
        searchMaxPrice: $("#search-max-price"),
        searchDistrict: $("#search-district"),
        searchFeature: $("#search-feature"),
        searchLimit: $("#search-limit"),
        // stats
        statsContainer: $("#stats-container"),
        // benchmark
        benchmarkContainer: $("#benchmark-container"),
        benchmarkRun: $("#benchmark-run"),
        // hero
        statTotal: $("#stat-total"),
        statAgents: $("#stat-agents"),
        statDistricts: $("#stat-districts"),
        // toast
        toastContainer: $("#toast-container"),
    };

    // ── Helpers ──────────────────────────────────────────────────────────
    function formatPrice(n) {
        return new Intl.NumberFormat("tr-TR").format(n);
    }

    function showToast(msg, type = "error") {
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        el.textContent = msg;
        dom.toastContainer.appendChild(el);
        setTimeout(() => {
            el.style.opacity = "0";
            el.style.transform = "translateX(40px)";
            el.style.transition = "all .3s";
            setTimeout(() => el.remove(), 350);
        }, 4000);
    }

    async function apiFetch(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.error || `HTTP ${res.status}`);
        }
        return res.json();
    }

    function renderLoading() {
        return `<div class="loading-state"><span class="loader"></span><p>Yükleniyor…</p></div>`;
    }

    function renderEmpty(msg) {
        return `<div class="empty-state"><span class="empty-icon">◇</span><p>${msg}</p></div>`;
    }

    // ── Listing Card ────────────────────────────────────────────────────
    function listingCardHTML(item, idx) {
        const initials = item.danisman
            .split(" ")
            .map((w) => w[0])
            .join("")
            .slice(0, 2);
        const delay = idx * 0.07;
        return `
        <article class="listing-card" style="animation-delay:${delay}s">
            <div class="card-header">
                <span class="card-id">#${item.ilan_id}</span>
                <span class="card-type">${item.emlak_tipi || "—"}</span>
            </div>
            <h3 class="card-title">${item.baslik}</h3>
            <div class="card-price">${formatPrice(item.fiyat)} <span class="currency">₺/ay</span></div>
            <div class="card-meta">
                <div class="meta-item">
                    <span class="meta-label">İlçe</span>
                    <span class="meta-value">${item.ilce || "—"}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Mahalle</span>
                    <span class="meta-value">${item.mahalle || "—"}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Brüt / Net</span>
                    <span class="meta-value">${item.brut_m2 ?? "—"} / ${item.net_m2 ?? "—"} m²</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Oda</span>
                    <span class="meta-value">${item.oda_sayisi || "—"}</span>
                </div>
            </div>
            <div class="card-footer">
                <div class="card-agent-avatar">${initials}</div>
                <span class="card-agent-name">${item.danisman}</span>
            </div>
        </article>`;
    }

    // ── Tab Navigation ──────────────────────────────────────────────────
    function activateTab(tabName) {
        dom.navLinks.forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.tab === tabName);
        });
        dom.panels.forEach((p) => {
            const isTarget = p.id === `panel-${tabName}`;
            p.classList.toggle("active", isTarget);
            if (isTarget) {
                p.style.animation = "none";
                void p.offsetHeight; // reflow
                p.style.animation = "";
            }
        });
        // Close mobile nav
        dom.navLinksContainer.classList.remove("open");
    }

    dom.navLinks.forEach((btn) => {
        btn.addEventListener("click", () => {
            activateTab(btn.dataset.tab);
            if (btn.dataset.tab === "listings") loadListings();
            if (btn.dataset.tab === "stats") loadStats();
        });
    });

    dom.mobileToggle.addEventListener("click", () => {
        dom.navLinksContainer.classList.toggle("open");
    });

    // ── Load Listings ───────────────────────────────────────────────────
    async function loadListings() {
        const sort = dom.listingsSort.value;
        const limit = dom.listingsLimit.value;
        dom.listingsGrid.innerHTML = renderLoading();
        try {
            const data = await apiFetch(`${API.listings}?sort_by=${sort}&limit=${limit}`);
            if (!data.length) {
                dom.listingsGrid.innerHTML = renderEmpty("Kayıt bulunamadı.");
                return;
            }
            dom.listingsGrid.innerHTML = data.map(listingCardHTML).join("");
        } catch (e) {
            dom.listingsGrid.innerHTML = renderEmpty("Yükleme hatası.");
            showToast(e.message);
        }
    }

    dom.listingsSort.addEventListener("change", loadListings);
    dom.listingsLimit.addEventListener("change", loadListings);

    // ── Search ──────────────────────────────────────────────────────────
    dom.searchForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const params = new URLSearchParams();
        const price = dom.searchMaxPrice.value;
        const district = dom.searchDistrict.value;
        const feature = dom.searchFeature.value;
        const limit = dom.searchLimit.value;
        if (price) params.set("max_price", price);
        if (district) params.set("district", district);
        if (feature) params.set("feature", feature);
        params.set("limit", limit);

        dom.searchGrid.innerHTML = renderLoading();
        try {
            const data = await apiFetch(`${API.search}?${params}`);
            if (!data.length) {
                dom.searchGrid.innerHTML = renderEmpty("Filtrelere uygun ilan bulunamadı.");
                return;
            }
            dom.searchGrid.innerHTML = data.map(listingCardHTML).join("");
        } catch (e) {
            dom.searchGrid.innerHTML = renderEmpty("Arama hatası.");
            showToast(e.message);
        }
    });

    // ── Stats ───────────────────────────────────────────────────────────
    async function loadStats() {
        dom.statsContainer.innerHTML = renderLoading();
        try {
            const data = await apiFetch(API.stats);
            if (!data.length) {
                dom.statsContainer.innerHTML = renderEmpty("İstatistik yok.");
                return;
            }
            const maxPortfoy = Math.max(...data.map((s) => s.toplam_portfoy));
            dom.statsContainer.innerHTML = data
                .map((s, i) => {
                    const pct = maxPortfoy > 0 ? (s.toplam_portfoy / maxPortfoy) * 100 : 0;
                    return `
                    <div class="stat-card" style="animation-delay:${i * 0.1}s">
                        <h3 class="stat-agent-name">${s.ad_soyad}</h3>
                        <div class="stat-row">
                            <div class="stat-item">
                                <span class="stat-number">${s.toplam_ilan}</span>
                                <span class="stat-label-text">İlan</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-number">${formatPrice(s.toplam_portfoy)}</span>
                                <span class="stat-label-text">Portföy (₺)</span>
                            </div>
                        </div>
                        <div class="portfolio-bar-track">
                            <div class="portfolio-bar-fill" data-width="${pct}"></div>
                        </div>
                    </div>`;
                })
                .join("");
            // Animate bars
            requestAnimationFrame(() => {
                dom.statsContainer.querySelectorAll(".portfolio-bar-fill").forEach((bar) => {
                    bar.style.width = bar.dataset.width + "%";
                });
            });
        } catch (e) {
            dom.statsContainer.innerHTML = renderEmpty("Yükleme hatası.");
            showToast(e.message);
        }
    }

    // ── Benchmark ───────────────────────────────────────────────────────
    dom.benchmarkRun.addEventListener("click", async () => {
        dom.benchmarkRun.disabled = true;
        dom.benchmarkRun.textContent = "Çalışıyor…";
        try {
            const data = await apiFetch(API.benchmark);
            const labels = {
                list_ms: "Listeleme",
                search_ms: "Arama",
                stats_ms: "İstatistik",
            };
            let html = '<div class="benchmark-results">';
            let i = 0;
            for (const [key, val] of Object.entries(data)) {
                html += `
                <div class="bench-card" style="animation-delay:${i * 0.12}s">
                    <div class="bench-label">${labels[key] || key}</div>
                    <div class="bench-value">${val.toFixed(2)}</div>
                    <div class="bench-unit">milisaniye</div>
                </div>`;
                i++;
            }
            html += "</div>";
            dom.benchmarkContainer.innerHTML =
                `<button class="btn-primary" id="benchmark-run"><span class="btn-icon">⚡</span> Tekrar Çalıştır</button>` +
                html;
            // Re-bind
            document.getElementById("benchmark-run").addEventListener("click", arguments.callee);
        } catch (e) {
            showToast(e.message);
        } finally {
            dom.benchmarkRun.disabled = false;
            dom.benchmarkRun.textContent = "⚡ Benchmark Çalıştır";
        }
    });

    // ── Load Meta (districts / features for search) ─────────────────────
    async function loadMeta() {
        try {
            const meta = await apiFetch(API.meta);
            // Populate district select
            meta.districts.forEach((d) => {
                const opt = document.createElement("option");
                opt.value = d;
                opt.textContent = d;
                dom.searchDistrict.appendChild(opt);
            });
            // Populate feature select
            meta.features.forEach((f) => {
                const opt = document.createElement("option");
                opt.value = f;
                opt.textContent = f;
                dom.searchFeature.appendChild(opt);
            });
            // Hero stats
            dom.statDistricts.textContent = meta.districts.length;
        } catch (e) {
            /* silent */
        }
    }

    // ── Load Hero Stats ─────────────────────────────────────────────────
    async function loadHeroStats() {
        try {
            const [listings, stats] = await Promise.all([
                apiFetch(`${API.listings}?limit=200`),
                apiFetch(API.stats),
            ]);
            dom.statTotal.textContent = listings.length;
            dom.statAgents.textContent = stats.length;
        } catch (e) {
            /* silent */
        }
    }

    // ── Init ────────────────────────────────────────────────────────────
    loadListings();
    loadMeta();
    loadHeroStats();
})();
