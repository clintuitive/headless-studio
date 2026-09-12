/* Progressive enhancement: track links remain playable without JavaScript. */
(() => {
  'use strict';
  const clock = seconds => {
    const n = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
    return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`;
  };
  // Include the standalone sketches in the one-at-a-time playback policy.
  document.addEventListener('play', event => {
    if (event.target instanceof HTMLMediaElement) {
      document.querySelectorAll('audio').forEach(audio => {
        if (audio !== event.target) audio.pause();
      });
    }
  }, true);
  document.querySelectorAll('.album-player').forEach(player => {
    const find = selector => player.querySelector(selector);
    const tracks = [...player.querySelectorAll('.album-track')];
    if (!tracks.length) return;
    const audio = document.createElement('audio');
    audio.preload = 'none';
    player.append(audio);
    const toggle = find('.toggle-play');
    const previous = find('.previous-track');
    const next = find('.next-track');
    const seek = find('.seek-track');
    const state = find('.playback-state');
    let index = 0;
    let request = 0;
    const title = () => tracks[index].querySelector('.track-name').textContent;
    function updatePlayback() {
      const playing = !audio.paused && !audio.ended;
      find('.play-label').textContent = playing ? 'Pause' : 'Play';
      find('.play-icon').textContent = playing ? 'Ⅱ' : '▶';
      toggle.setAttribute('aria-label', `${playing ? 'Pause' : 'Play'} ${title()}`);
      player.classList.toggle('is-playing', playing);
    }
    function updateTime() {
      const valid = Number.isFinite(audio.duration) && audio.duration > 0;
      seek.disabled = !valid;
      seek.max = valid ? audio.duration : 100;
      seek.value = audio.currentTime || 0;
      seek.setAttribute('aria-valuetext', `${clock(audio.currentTime)} of ${valid ? clock(audio.duration) : find('.track-length').textContent}`);
      find('.elapsed').textContent = clock(audio.currentTime);
      if (valid) find('.track-length').textContent = clock(audio.duration);
    }
    async function play() {
      const current = ++request;
      state.textContent = 'Loading…';
      try {
        if (audio.error) audio.load();
        await audio.play();
      } catch (error) {
        if (current !== request || error.name === 'AbortError') return;
        state.textContent = 'Playback could not start. Press Play to try again.';
        updatePlayback();
      }
    }
    function select(n, autoplay = false) {
      ++request;
      audio.pause();
      index = n;
      audio.src = tracks[index].href;
      find('.current-title').textContent = title();
      find('.track-length').textContent = tracks[index].querySelector('.track-duration').textContent;
      tracks.forEach((track, i) => {
        track.classList.toggle('is-current', i === index);
        if (i === index) track.setAttribute('aria-current', 'true');
        else track.removeAttribute('aria-current');
      });
      next.disabled = index === tracks.length - 1;
      state.textContent = 'Ready to play';
      updatePlayback();
      updateTime();
      if (autoplay) play();
    }
    tracks.forEach((track, n) => track.addEventListener('click', event => {
      // Preserve open-in-new-tab and download link behavior.
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      select(n, true);
    }));
    toggle.addEventListener('click', () => {
      if (audio.paused) play();
      else { ++request; audio.pause(); }
    });
    previous.addEventListener('click', () => {
      const wasPlaying = !audio.paused;
      if (audio.currentTime > 3 || index === 0) { audio.currentTime = 0; updateTime(); }
      else select(index - 1, wasPlaying);
    });
    next.addEventListener('click', () => {
      if (index < tracks.length - 1) select(index + 1, !audio.paused);
    });
    seek.addEventListener('input', () => {
      if (Number.isFinite(audio.duration)) audio.currentTime = Number(seek.value);
      updateTime();
    });
    audio.addEventListener('play', () => { state.textContent = 'Now playing'; updatePlayback(); });
    audio.addEventListener('pause', () => { state.textContent = 'Paused'; updatePlayback(); });
    audio.addEventListener('playing', () => { state.textContent = 'Now playing'; });
    audio.addEventListener('waiting', () => { if (!audio.paused) state.textContent = 'Buffering…'; });
    audio.addEventListener('error', () => {
      state.textContent = 'This track could not load. Choose another track or press Play to retry.';
      updatePlayback();
    });
    ['timeupdate', 'loadedmetadata', 'durationchange'].forEach(event => audio.addEventListener(event, updateTime));
    audio.addEventListener('ended', () => {
      if (index < tracks.length - 1) select(index + 1, true);
      else { state.textContent = 'Album complete'; updatePlayback(); }
    });
    select(0);
    find('.album-console').hidden = false;
  });
})();
