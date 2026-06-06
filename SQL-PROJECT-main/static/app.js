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
        analytics: "/api/analytics",
        listingHistory: "/api/listing-history",
        meta: "/api/meta",
    };

    // ── DOM Cache ────────────────────────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        navLinks: $$("#nav-links .nav-link[data-tab]"),
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
        // analytics
        analyticsContainer: $("#analytics-container"),
        analyticsLimit: $("#analytics-limit"),
        // audit
        auditContainer: $("#audit-container"),
        auditLimit: $("#audit-limit"),
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

    function renderTable(headers, rows) {
        if (!rows.length) return renderEmpty("Kayıt bulunamadı.");
        return `
        <div class="data-table-wrap">
            <table class="data-table">
                <thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
                <tbody>
                    ${rows
                        .map(
                            (row) =>
                                `<tr>${row.map((cell) => `<td>${cell ?? "—"}</td>`).join("")}</tr>`
                        )
                        .join("")}
                </tbody>
            </table>
        </div>`;
    }

    function renderAnalysisCard(title, subtitle, tableHTML) {
        return `
        <article class="analysis-card">
            <div class="analysis-card-head">
                <h3>${title}</h3>
                <span>${subtitle}</span>
            </div>
            ${tableHTML}
        </article>`;
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
        <a class="listing-card listing-card--link" href="/listing/${item.ilan_id}" style="animation-delay:${delay}s">
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
                <span class="card-detail-cta">Detay →</span>
            </div>
        </a>`;
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
            if (btn.dataset.tab === "analytics") loadAnalytics();
            if (btn.dataset.tab === "audit") loadAudit();
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
    async function runBenchmark() {
        const btn = document.getElementById("benchmark-run");
        if (btn) btn.disabled = true;
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
            document.getElementById("benchmark-run").addEventListener("click", runBenchmark);
        } catch (e) {
            showToast(e.message);
        } finally {
            const b = document.getElementById("benchmark-run");
            if (b) b.disabled = false;
        }
    }

    dom.benchmarkRun.addEventListener("click", runBenchmark);

    // ── Advanced Analytics ─────────────────────────────────────────────────────
    async function loadAnalytics() {
        const limit = dom.analyticsLimit.value;
        dom.analyticsContainer.innerHTML = renderLoading();
        try {
            const data = await apiFetch(`${API.analytics}?limit=${limit}`);

            const regionRows = data.region_analysis.map((r) => [
                r["İlce"],
                r.IlanSayisi,
                formatPrice(r.OrtalamaFiyat),
                formatPrice(r.OrtalamaNetM2Fiyati),
                formatPrice(r.FiyatAraligi),
            ]);
            const rankingRows = data.listing_ranking.map((r) => [
                `#${r.IlanID}`,
                r["İlce"],
                formatPrice(r.Fiyat),
                r.IlceIciFiyatSirasi,
                r.GenelFiyatSirasi,
            ]);
            const agentRows = data.agent_ranking.map((r) => [
                r.AdSoyad,
                r.ToplamIlan,
                formatPrice(r.ToplamPortfoy),
                r.PortfoyDegeriSirasi,
                r.IlanSayisiSirasi,
            ]);
            const pivotRows = data.room_pivot.map((r) => [
                r["İlce"],
                r.Oda_1_1,
                r.Oda_2_1,
                r.Diger,
                r.Toplam,
            ]);

            dom.analyticsContainer.innerHTML = `
                <div class="analysis-grid">
                    ${renderAnalysisCard(
                        "Bölge Fiyatları",
                        "Piyasa Özeti",
                        renderTable(["İlçe", "İlan", "Ort. Fiyat", "Ort. Net m²", "Aralık"], regionRows)
                    )}
                    ${renderAnalysisCard(
                        "En Değerli İlanlar",
                        "Fiyat Sıralaması",
                        renderTable(["İlan", "İlçe", "Fiyat", "İlçe Sıra", "Genel Sıra"], rankingRows)
                    )}
                    ${renderAnalysisCard(
                        "Danışman Performansı",
                        "Portföy Özeti",
                        renderTable(["Danışman", "İlan", "Portföy", "Portföy Sıra", "İlan Sıra"], agentRows)
                    )}
                    ${renderAnalysisCard(
                        "Oda Dağılımı",
                        "Bölge Karşılaştırması",
                        renderTable(["İlçe", "1+1", "2+1", "Diğer", "Toplam"], pivotRows)
                    )}
                </div>`;
        } catch (e) {
            dom.analyticsContainer.innerHTML = renderEmpty("Analiz yüklenemedi.");
            showToast(e.message);
        }
    }

    dom.analyticsLimit.addEventListener("change", loadAnalytics);

    // ── Audit Log ──────────────────────────────────────────────────────────────
    async function loadAudit() {
        const limit = dom.auditLimit.value;
        dom.auditContainer.innerHTML = renderLoading();
        try {
            const data = await apiFetch(`${API.listingHistory}?limit=${limit}`);
            if (!data.length) {
                dom.auditContainer.innerHTML = renderEmpty("Henüz ilan değişikliği yapılmadı.");
                return;
            }
            const rows = data.map((r) => [
                r.LogID,
                `#${r.IlanID}`,
                r.IslemTipi,
                r.AlanAdi || "İlan",
                r.EskiDeger || "—",
                r.YeniDeger || "—",
                r.Kullanici,
                r.DegisimTarihi,
            ]);
            dom.auditContainer.innerHTML = renderTable(
                ["Log", "İlan", "İşlem", "Alan", "Eski", "Yeni", "Kullanıcı", "Tarih"],
                rows
            );
        } catch (e) {
            dom.auditContainer.innerHTML = renderEmpty("İlan geçmişi yüklenemedi.");
            showToast(e.message);
        }
    }

    dom.auditLimit.addEventListener("change", loadAudit);

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
