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
