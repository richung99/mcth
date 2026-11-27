// -----------------------------------------------------------------------------
// player.js
// Keeps the drink menu video playing on the TV.
// The video is ONE pre-built file with the promos already baked in at fixed
// points (scripts/build_drink_video.py), and the <video> element loops it with
// the browser's own "loop". This script never seeks, switches files or reloads
// the page during normal playback; it only steps in if the TV gets stuck.
// Depends on: the <video class="menu-video" loop autoplay ...> in index.html.
// Does NOT handle: building the video (build script) or what's in it
//   (<page>/playlist.json). A new build shows up the next time the page loads.
// -----------------------------------------------------------------------------

(function () {
	const STALL_LIMIT_S = 15; // frozen this long -> reload the video

	const video = document.querySelector(".menu-video");
	const debugBox = document.getElementById("debug");
	const DEBUG = /[?&]debug\b/.test(location.search);
	const log = [];
	let lastTime = -1;
	let stalledFor = 0;
	let loops = 0;

	video.muted = true; // muted video is allowed to start on its own (no click needed)

	// --- Cover: a still of the video's first frame, laid over the video ---------
	// TVs fade the screen to black whenever the video restarts (every loop) or
	// waits for data. The cover hides that: it goes up just before the end of the
	// file and whenever the video isn't moving, and comes down only once the video
	// is moving again. The first 7s and last 0.9s of the file are the still board,
	// identical to the cover, so the swaps are invisible.
	const cover = document.querySelector(".menu-cover");
	const END_MARGIN_S = 0.4;   // cover goes up this close to the end of the file
	const START_CLEAR_S = 5;    // after a restart, cover stays until this point (still board until 7.1s)
	const MOVING_FOR_MS = 400;  // mid-file: cover comes down after moving this long
	const FROZEN_MS = 1000;     // time unchanged this long = "not moving" (some TVs update currentTime coarsely)
	let coverUp = true;
	let coverT = -1;
	let changedAt = 0;
	let movingSince = 0;

	function setCover(up, why) {
		if (!cover || up === coverUp) return;
		coverUp = up;
		cover.classList.toggle("hidden", !up);
		note("cover " + (up ? "up (" + why + ")" : "down") + " at " + video.currentTime.toFixed(1) + "s");
	}

	["seeking", "waiting", "emptied", "error"].forEach((ev) =>
		video.addEventListener(ev, () => { movingSince = 0; setCover(true, ev); }));

	setInterval(() => {
		const t = video.currentTime;
		const d = video.duration;
		const now = Date.now();
		if (t !== coverT) { coverT = t; changedAt = now; }
		const moving = !video.paused && !video.error && changedAt > 0 && now - changedAt < FROZEN_MS;
		if (!moving) { movingSince = 0; setCover(true, "not moving"); return; }
		if (!movingSince) movingSince = now;
		if (d && t >= d - END_MARGIN_S) { setCover(true, "end of file"); return; }
		if (coverUp && t > 0.05 && (t < 7 ? t >= START_CLEAR_S : now - movingSince >= MOVING_FOR_MS)) setCover(false);
	}, 100);

	/** Add a line to the ?debug overlay's event log. */
	function note(msg) {
		if (!DEBUG) return;
		log.unshift(new Date().toLocaleTimeString() + "  " + msg);
		log.length = Math.min(log.length, 8);
	}

	/** Start or resume playback, logging (not throwing) if the browser refuses. */
	function start() {
		const p = video.play();
		if (p && p.catch) p.catch((e) => note("play() refused: " + e.name));
	}

	video.addEventListener("seeked", () => {
		if (video.currentTime < 1) note("looped (" + ++loops + ")");
	});
	video.addEventListener("waiting", () => note("waiting for data at " + video.currentTime.toFixed(1) + "s"));
	video.addEventListener("error", () => {
		note("video failed to load (code " + (video.error && video.error.code) + "), retrying");
		setTimeout(() => { video.load(); start(); }, 3000);
	});

	// Once a second: update the ?debug box; resume if paused; if the video stays
	// frozen for STALL_LIMIT_S (TV hiccup, network blip), reload it.
	setInterval(() => {
		if (DEBUG) {
			debugBox.hidden = false;
			debugBox.textContent =
				video.currentSrc.split("/").pop() + "   time " + video.currentTime.toFixed(1) + " / " +
				(video.duration || 0).toFixed(1) + "   paused=" + video.paused +
				"   ready=" + video.readyState +
				(video.error ? "   ERROR code " + video.error.code : "") + "\n\n" + log.join("\n");
		}
		if (video.error) return;
		if (video.paused) start();
		if (video.currentTime === lastTime) {
			if (++stalledFor >= STALL_LIMIT_S) {
				note("stuck at " + video.currentTime.toFixed(1) + "s, reloading");
				stalledFor = 0;
				video.load();
				start();
			}
		} else {
			stalledFor = 0;
		}
		lastTime = video.currentTime;
	}, 1000);

	start();
})();
