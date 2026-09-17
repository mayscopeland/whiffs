(() => {
  const INDEX_URL = "/assets/data/players-index.json";
  const MAX_RESULTS = 10;

  let players = null;
  let loadPromise = null;
  let activeIndex = -1;

  function normalizeSearchText(text) {
    return String(text)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "");
  }

  function loadIndex() {
    if (players) return Promise.resolve(players);
    if (loadPromise) return loadPromise;
    loadPromise = fetch(INDEX_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load player index (${res.status})`);
        return res.json();
      })
      .then((data) => {
        players = (Array.isArray(data) ? data : []).map((player) => ({
          ...player,
          searchKey: normalizeSearchText(player.name || ""),
        }));
        return players;
      })
      .catch((err) => {
        loadPromise = null;
        console.error(err);
        players = [];
        return players;
      });
    return loadPromise;
  }

  function filterPlayers(query) {
    const q = normalizeSearchText(query);
    if (!q || !players) return [];
    const results = [];
    for (const player of players) {
      if ((player.searchKey || "").includes(q)) {
        results.push(player);
        if (results.length >= MAX_RESULTS) break;
      }
    }
    return results;
  }

  function renderResults(listEl, results, query) {
    activeIndex = -1;
    if (!query.trim() || results.length === 0) {
      listEl.innerHTML = "";
      listEl.classList.add("hidden");
      return;
    }

    listEl.innerHTML = results
      .map(
        (player, i) => `
      <li role="option" id="player-search-option-${i}" data-index="${i}">
        <a
          href="/players/${player.id}/"
          class="player-search-option block px-3 py-2 text-sm text-slate-100 hover:bg-slate-700 focus:bg-slate-700 focus:outline-none truncate"
          data-index="${i}"
        >${escapeHtml(player.name)}</a>
      </li>`
      )
      .join("");
    listEl.classList.remove("hidden");
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setActive(listEl, index) {
    const options = listEl.querySelectorAll(".player-search-option");
    options.forEach((el) => el.classList.remove("bg-slate-700"));
    if (index < 0 || index >= options.length) {
      activeIndex = -1;
      return;
    }
    activeIndex = index;
    options[index].classList.add("bg-slate-700");
    options[index].scrollIntoView({ block: "nearest" });
  }

  function close(listEl, input) {
    listEl.innerHTML = "";
    listEl.classList.add("hidden");
    activeIndex = -1;
    input.setAttribute("aria-expanded", "false");
  }

  function initSearch(root) {
    const input = root.querySelector("[data-player-search-input]");
    const listEl = root.querySelector("[data-player-search-results]");
    if (!input || !listEl) return;

    let debounceTimer = null;

    const runSearch = () => {
      const query = input.value;
      const results = filterPlayers(query);
      renderResults(listEl, results, query);
      input.setAttribute("aria-expanded", results.length > 0 ? "true" : "false");
    };

    input.addEventListener("focus", () => {
      loadIndex().then(runSearch);
    });

    input.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadIndex().then(runSearch);
      }, 40);
    });

    input.addEventListener("keydown", (event) => {
      const options = listEl.querySelectorAll(".player-search-option");
      if (event.key === "ArrowDown") {
        if (options.length === 0) return;
        event.preventDefault();
        setActive(listEl, Math.min(activeIndex + 1, options.length - 1));
      } else if (event.key === "ArrowUp") {
        if (options.length === 0) return;
        event.preventDefault();
        setActive(listEl, Math.max(activeIndex - 1, 0));
      } else if (event.key === "Enter") {
        if (activeIndex >= 0 && options[activeIndex]) {
          event.preventDefault();
          options[activeIndex].click();
        }
      } else if (event.key === "Escape") {
        close(listEl, input);
        input.blur();
      }
    });

    document.addEventListener("click", (event) => {
      if (!root.contains(event.target)) {
        close(listEl, input);
      }
    });
  }

  document.querySelectorAll("[data-player-search]").forEach(initSearch);
})();
