// -----------------------------------------------------------------------------
// player.js
// Plays the drink menu on the TV: loops the menu section of the combined video
// and, every few minutes, plays the next promo (they take turns) — all inside ONE
// video file, so the TV never blinks. Also picks up new builds automatically.
// Depends on: drink/segments.json + img/drink_menu_loop.mp4 (both written by
//   scripts/build_drink_video.py), the <video class="menu-video"> in index.html.
// Does NOT handle: joining/encoding videos (build script) or deciding which
//   videos exist (drink/playlist.json).
// -----------------------------------------------------------------------------

(function () {
	const SEGMENTS_URL = "segments.json";
	const FALLBACK_VIDEO = "../img/drink_menu_loop.mp4";
	const UPDATE_CHECK_MS = 5 * 60 * 1000; // how often to look for a new build
	const STALL_LIMIT_S = 15;              // frozen this long -> reload the video

	const video = document.querySelector(".menu-video");
	const debugBox = document.getElementById("debug");
	const DEBUG = /[?&]debug\b/.test(location.search);
	const log = [];

	let segments = null;       // contents of segments.json, or null if unavailable
	let section = "menu";      // which section is on screen: "menu" or "promo 1", "promo 2"...
	let promoIndex = 0;        // which promo plays next (they alternate in playlist order)
	let activePromo = null;    // the promo segment currently playing, or null
	let nextPromoAt = Infinity; // Date.now() value after which the promo is due
	let reloadPending = false; // a new build exists; reload at the next loop end
	let lastTime = -1;
	let stalledFor = 0;

	// Muted video is allowed to start on its own (no click needed)
	video.muted = true;

	/** Add a line to the ?debug overlay's event log. */
	function note(msg) {
		if (!DEBUG) return;
		log.unshift(new Date().toLocaleTimeString() + "  " + msg);
		log.length = Math.min(log.length, 8);
	}

	/** Start or resume playback, logging (not throwing) if the browser refuses. */
	function play() {
		const p = video.play();
		if (p && p.catch) p.catch((e) => note("play() refused: " + e.name));
	}

	/**
	 * Fetch segments.json, bypassing every cache.
	 *
	 * @returns The parsed segments object, or null if it can't be loaded.
	 *
	 * @remarks
	 * The "?nc=" timestamp stops TV browsers and GitHub's CDN from handing back
	 * an old copy, which would hide a new build.
	 */
	async function fetchSegments() {
		try {
			const res = await fetch(SEGMENTS_URL + "?nc=" + Date.now(), { cache: "no-store" });
			if (!res.ok) throw new Error("HTTP " + res.status);
			return await res.json();
		} catch (e) {
			note("couldn't load segments.json (" + e.message + ")");
			return null;
		}
	}

	/**
	 * Jump to the start of a section and keep playing.
	 *
	 * @param name - "menu" or "promo".
	 * @param seg  - The segment ({start, end}) to jump to.
	 *
	 * @remarks
	 * Seeks half a frame past the section start. The start times in
	 * segments.json are rounded to 4 decimals, so seeking to the exact number
	 * could land on the last frame of the PREVIOUS section.
	 * Seeking inside the same file never blanks the screen: the current frame
	 * stays up until the new one is ready. That's the whole point of one file.
	 */
	function jumpTo(name, seg) {
		section = name;
		video.currentTime = seg.start + 0.5 / segments.fps;
		play();
		note("playing " + name);
	}

	/**
	 * Decide what plays after the menu loop reaches the end of the file.
	 *
	 * @remarks
	 * Order of checks:
	 * 1. A new build was found -> reload the page now. This is the one moment a
	 *    reload is least noticeable: the board on screen matches what the new
	 *    file starts with. (It's the only planned blink, once per update.)
	 * 2. A promo is due -> jump to the next promo in the rotation. The promos
	 *    sit one after another at the start of the file, so promoEnded()
	 *    (below) sends every promo except the last one back to the menu.
	 * 3. Otherwise -> jump back to the start of the menu section.
	 */
	function onEnded() {
		// A new build (or segments.json finally loading) wins over everything
		if (reloadPending) {
			note("new build found, reloading");
			location.reload();
			return;
		}
		// Fallback mode (no segments.json): just loop the whole file
		if (!segments) {
			video.currentTime = 0;
			play();
			return;
		}
		// Promo due -> promo; otherwise loop the menu
		if (segments.promos.length && Date.now() >= nextPromoAt) {
			nextPromoAt = Date.now() + segments.promoEveryMinutes * 60 * 1000;
			const i = promoIndex;
			promoIndex = (promoIndex + 1) % segments.promos.length;
			activePromo = segments.promos[i];
			jumpTo("promo " + (i + 1), activePromo);
		} else {
			activePromo = null;
			jumpTo("menu", segments.menu);
		}
	}

	/** Check for a newer build and, if there is one, schedule a reload. */
	async function checkForUpdate() {
		const latest = await fetchSegments();
		if (!latest) return;
		if (!segments || latest.version !== segments.version) {
			reloadPending = true;
			note("new build " + latest.version + " will load at the next loop end");
		}
	}

	/**
	 * While a promo plays, notice the instant it finishes (checked every 50ms).
	 *
	 * @remarks
	 * The last promo in the file runs straight into the menu on its own. Any
	 * earlier promo is followed by the NEXT promo in the file, which we don't
	 * want yet, so we jump to the menu start the moment it ends. Every promo
	 * starts and ends on the plain menu board, so a jump of a frame or two
	 * early or late is invisible, and it's a seek inside the file, so no blink.
	 * The "ended" event can't be used for this: it only fires at the file's end.
	 */
	function promoEnded() {
		if (!activePromo || video.seeking) return;
		if (video.currentTime < activePromo.end - 0.04) return;

		const finished = activePromo;
		activePromo = null;
		if (finished.end < segments.menu.start - 0.001) {
			jumpTo("menu", segments.menu);
			note("promo finished, jumped to menu");
		} else {
			section = "menu"; // last promo: already flowing into the menu
			note("promo finished, back to menu");
		}
	}

	/** Redraw the ?debug overlay. */
	function renderDebug() {
		if (!DEBUG) return;
		const secs = Math.max(0, Math.round((nextPromoAt - Date.now()) / 1000));
		debugBox.hidden = false;
		debugBox.textContent =
			"section: " + section + "   time " + video.currentTime.toFixed(1) + " / " +
			(video.duration || 0).toFixed(1) + "   paused=" + video.paused +
			"   ready=" + video.readyState + (video.error ? "   ERROR code " + video.error.code : "") + "\n" +
			(segments
				? "build " + segments.version + "   " +
				  (segments.promos.length
					? "next: promo " + (promoIndex + 1) + " of " + segments.promos.length + " after this loop, in ≥ " + secs + "s"
					: "no promos in playlist")
				: "segments.json unavailable: looping whole file") +
			(reloadPending ? "   (reload pending)" : "") + "\n\n" + log.join("\n");
	}

	/**
	 * Once a second: keep the overlay current and recover from TV hiccups.
	 *
	 * @remarks
	 * - Paused for no reason -> resume.
	 * - "ended" event missed (some TV browsers drop it) -> run onEnded().
	 * - Playhead frozen for STALL_LIMIT_S -> reload the video and restart the
	 *   menu. That reload does blink, but only in an actual failure.
	 * - Promo section finished -> mark the menu as on screen again.
	 */
	function watchdog() {
		renderDebug();
		if (video.error) return; // the "error" handler deals with it

		// Recover from missed events, pauses and freezes
		if (video.ended) {
			onEnded();
		} else if (video.paused) {
			play();
		}
		if (video.currentTime === lastTime) {
			if (++stalledFor >= STALL_LIMIT_S) {
				note("stuck at " + video.currentTime.toFixed(1) + "s, reloading video");
				stalledFor = 0;
				video.load();
			}
		} else {
			stalledFor = 0;
		}
		lastTime = video.currentTime;
	}

	/**
	 * Load the build info, point the video at the combined file and start.
	 *
	 * @remarks
	 * The video URL carries the build version ("?v=...") so a TV that cached an
	 * older drink_menu_loop.mp4 is forced to fetch the new one.
	 * If segments.json can't be loaded, the page still works: it loops the
	 * whole file (promo included) until a later update check succeeds.
	 */
	async function start() {
		segments = await fetchSegments();

		// Every (re)load of the file starts at the menu section
		video.addEventListener("loadedmetadata", () => {
			if (segments) jumpTo("menu", segments.menu);
			else play();
		});
		video.addEventListener("ended", onEnded);
		video.addEventListener("error", () => {
			note("video failed to load (code " + (video.error && video.error.code) + "), retrying");
			setTimeout(() => video.load(), 3000);
		});

		if (segments) {
			nextPromoAt = Date.now() + segments.promoEveryMinutes * 60 * 1000;
			video.src = "../" + segments.video + "?v=" + segments.version;
		} else {
			video.src = FALLBACK_VIDEO;
		}

		setInterval(watchdog, 1000);
		setInterval(promoEnded, 50);
		setInterval(checkForUpdate, UPDATE_CHECK_MS);
	}

	start();
})();
