const homeView = document.querySelector("#home");
const gameView = document.querySelector("#game");
const modeCards = document.querySelectorAll(".mode-card[data-mode]");
const sessionButtons = document.querySelectorAll("[data-session-type]");
const arcadeOptionField = document.querySelector("#arcade-option-field");
const timedOptionField = document.querySelector("#timed-option-field");
const arcadeCount = document.querySelector("#arcade-count");
const timedDuration = document.querySelector("#timed-duration");
const setupNote = document.querySelector("#setup-note");
const backButton = document.querySelector("#back-button");
const playButton = document.querySelector("#play-button");
const playButtonLabel = playButton.querySelector(".button-label");
const submitButton = document.querySelector("#submit-button");
const submitButtonLabel = submitButton.querySelector(".button-label");
const lyricsFrame = document.querySelector("#lyrics-frame");
const lyricsBox = document.querySelector("#lyrics-box");
const finishContextTools = document.querySelector("#finish-context-tools");
const revealContextButton = document.querySelector("#reveal-context-button");
const contextStatus = document.querySelector("#context-status");
const audioBox = document.querySelector("#audio-box");
const audioPlayer = document.querySelector("#audio-player");
const albumBox = document.querySelector("#album-box");
const albumImage = document.querySelector("#album-image");
const promptTitle = document.querySelector("#prompt-title");
const gameTitle = document.querySelector("#game-title");
const modePill = document.querySelector("#mode-pill");
const sessionPill = document.querySelector("#session-pill");
const scoreValue = document.querySelector("#score-value");
const progressValue = document.querySelector("#progress-value");
const timerValue = document.querySelector("#timer-value");
const guessPanelTitle = document.querySelector("#guess-panel-title");
const guessForm = document.querySelector("#guess-form");
const songField = document.querySelector("#song-field");
const songInput = document.querySelector("#song-input");
const albumField = document.querySelector("#album-field");
const albumInput = document.querySelector("#album-input");
const lyricField = document.querySelector("#lyric-field");
const lyricInput = document.querySelector("#lyric-input");
const artistField = document.querySelector("#artist-field");
const artistInput = document.querySelector("#artist-input");
const resultMessage = document.querySelector("#result-message");
const answerMessage = document.querySelector("#answer-message");
const breakdownMessage = document.querySelector("#breakdown-message");
const loadingIndicator = document.querySelector("#loading-indicator");
const loadingCopy = document.querySelector("#loading-copy");

let currentMode = "album";
let currentSessionType = "classic";
let currentSessionId = null;
let currentRound = null;
let timerInterval = null;
let timerEndAt = null;
let isEndingTimedSession = false;
let revealedContextCount = 0;

const modeConfig = {
  album: {
    title: "Album Cover",
    pill: "Album",
    prompt: "Album Cover",
    guessTitle: "Song + Album + Artist",
    loading: "Loading album cover...",
    empty: "Pick a mode to start.",
    requiresAlbum: true,
    usesLyricInput: false,
  },
  lyrics: {
    title: "Guess the Lyric",
    pill: "Lyrics",
    prompt: "Lyrics",
    guessTitle: "Song + Artist",
    loading: "Loading lyrics...",
    empty: "Pick a mode to start.",
    requiresAlbum: false,
    usesLyricInput: false,
  },
  song: {
    title: "Guess the Song",
    pill: "Preview",
    prompt: "Preview",
    guessTitle: "Song + Artist",
    loading: "Loading preview...",
    empty: "Pick a mode to start.",
    requiresAlbum: false,
    usesLyricInput: false,
  },
  finish: {
    title: "Finish the Lyric",
    pill: "Finish",
    prompt: "Fill the missing words",
    guessTitle: "Missing lyric",
    loading: "Loading lyric gap...",
    empty: "Pick a mode to start.",
    requiresAlbum: false,
    usesLyricInput: true,
  },
};

const sessionCopy = {
  classic: "One round at a time, perfect for quick play.",
  arcade: "Pick 10 to 30 songs and play through the full stack for the best total score.",
  timed: "Pick a timer from 30 seconds up to 3 minutes and chase as many guesses as you can.",
};

function showView(viewName) {
  homeView.classList.toggle("active", viewName === "home");
  gameView.classList.toggle("active", viewName === "game");
}

function setLoading(isLoading, message = "Loading round...") {
  loadingIndicator.classList.toggle("hidden", !isLoading);
  loadingCopy.textContent = message;
  playButton.disabled = isLoading;
  submitButton.disabled = isLoading || !currentSessionId;
  playButtonLabel.textContent = isLoading ? "Loading..." : "Play Again";
}

function setSubmitState(disabled, label = "Submit Guess") {
  submitButton.disabled = disabled;
  submitButtonLabel.textContent = label;
}

function setResult(message = "", status = "") {
  resultMessage.textContent = message;
  resultMessage.className = "result-message";
  if (status) {
    resultMessage.classList.add(status);
  }
}

function resetAudio() {
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  audioPlayer.load();
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  timerEndAt = null;
}

function updateSetupControls() {
  sessionButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.sessionType === currentSessionType);
  });

  arcadeOptionField.classList.toggle("hidden", currentSessionType !== "arcade");
  timedOptionField.classList.toggle("hidden", currentSessionType !== "timed");
  setupNote.textContent = sessionCopy[currentSessionType];
}

function clearFeedback() {
  setResult("", "");
  answerMessage.textContent = "";
  breakdownMessage.textContent = "";
}

function resetInputs() {
  songInput.value = "";
  albumInput.value = "";
  lyricInput.value = "";
  artistInput.value = "";
}

function hasAnyGuess() {
  return [songInput.value, albumInput.value, lyricInput.value, artistInput.value].some((value) => value.trim());
}

function updateGuessFields(mode) {
  const config = modeConfig[mode];
  const isFinishMode = Boolean(config.usesLyricInput);

  songField.classList.toggle("hidden", isFinishMode);
  artistField.classList.toggle("hidden", isFinishMode);
  albumField.classList.toggle("hidden", !config.requiresAlbum);
  lyricField.classList.toggle("hidden", !isFinishMode);
  guessPanelTitle.textContent = config.guessTitle;
  songInput.required = false;
  artistInput.required = false;
  albumInput.required = false;
  lyricInput.required = false;
  songInput.placeholder = config.requiresAlbum ? "Type the song title if you know it" : "Type the song title";
  artistInput.placeholder = "Type the artist if you know it";
  albumInput.placeholder = "Type the album name if you know it";
  lyricInput.placeholder = "Type the missing words";
}

function applyModeChrome(mode) {
  const config = modeConfig[mode];
  currentMode = mode;
  gameTitle.textContent = config.title;
  promptTitle.textContent = config.prompt;
  modePill.textContent = config.pill;
  sessionPill.textContent = currentSessionType[0].toUpperCase() + currentSessionType.slice(1);
  updateGuessFields(mode);
}

function resetPrompt(copy) {
  currentRound = null;
  revealedContextCount = 0;
  lyricsFrame.classList.add("hidden");
  finishContextTools.classList.add("hidden");
  audioBox.classList.add("hidden");
  albumBox.classList.add("hidden");
  lyricsBox.textContent = copy;
  contextStatus.textContent = "";
  revealContextButton.disabled = true;
  albumImage.removeAttribute("src");
  resetAudio();
}

function getFinishPromptText(prompt) {
  const revealedLines = (prompt.context_lines || []).slice(0, revealedContextCount);
  const sections = [
    prompt.prompt_text,
    prompt.blanks,
    "",
    `${prompt.missing_word_count} word${prompt.missing_word_count === 1 ? "" : "s"} missing`,
  ];

  if (revealedLines.length > 0) {
    sections.push("");
    sections.push("Context:");
    revealedLines.forEach((line) => sections.push(line));
  }

  return sections.join("\n");
}

function updateFinishContextUI(prompt) {
  const totalContext = (prompt.context_lines || []).length;
  const remaining = Math.max(0, totalContext - revealedContextCount);

  finishContextTools.classList.toggle("hidden", currentMode !== "finish");

  if (currentMode !== "finish") {
    return;
  }

  contextStatus.textContent = totalContext
    ? `${revealedContextCount}/${totalContext} context lines revealed`
    : "No extra context available for this lyric.";
  revealContextButton.disabled = remaining === 0;
  revealContextButton.textContent = remaining === 0 ? "No More Context" : "Reveal More Context";
}

function setProgress(progress) {
  scoreValue.textContent = `${progress.score ?? 0}`;

  if (currentSessionType === "timed") {
    progressValue.textContent = `${progress.round_index || 0} guessed`;
  } else if (progress.total_rounds) {
    progressValue.textContent = `Round ${progress.round_index}/${progress.total_rounds}`;
  } else {
    progressValue.textContent = `Round ${progress.round_index || 1}`;
  }
}

function renderTimer(seconds) {
  if (seconds == null) {
    timerValue.textContent = "-";
    return;
  }

  timerValue.textContent = `${seconds}s`;
}

async function endTimedSession() {
  if (!currentSessionId || isEndingTimedSession) {
    return;
  }

  isEndingTimedSession = true;
  stopTimer();
  setSubmitState(true, "Time Up");

  try {
    const response = await fetch("/api/session/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Could not finish the timed run.");
    }

    currentSessionId = null;
    currentRound = null;
    renderTimer(0);
    setProgress(data.progress || { score: data.score, round_index: 0 });
    setResult("Time is up.", "fail");
    answerMessage.textContent = `Final score: ${data.score}`;
  } catch (error) {
    setResult(error.message, "fail");
  } finally {
    isEndingTimedSession = false;
  }
}

function syncTimer(secondsRemaining) {
  stopTimer();
  renderTimer(secondsRemaining);

  if (secondsRemaining == null) {
    return;
  }

  timerEndAt = Date.now() + secondsRemaining * 1000;
  timerInterval = setInterval(() => {
    const secondsLeft = Math.max(0, Math.ceil((timerEndAt - Date.now()) / 1000));
    renderTimer(secondsLeft);

    if (secondsLeft <= 0) {
      endTimedSession();
    }
  }, 250);
}

function renderRound(round) {
  currentRound = round;
  clearFeedback();
  resetInputs();
  applyModeChrome(round.mode);
  setProgress(round.progress || { score: 0, round_index: 1 });
  syncTimer(round.progress?.time_remaining ?? null);
  revealedContextCount = 0;

  lyricsFrame.classList.toggle("hidden", !["lyrics", "finish"].includes(round.mode));
  audioBox.classList.toggle("hidden", round.mode !== "song");
  albumBox.classList.toggle("hidden", round.mode !== "album");
  finishContextTools.classList.toggle("hidden", round.mode !== "finish");

  if (round.mode === "lyrics") {
    lyricsBox.textContent = round.prompt.lyrics;
  } else if (round.mode === "song") {
    audioPlayer.src = round.prompt.preview_url;
    audioPlayer.load();
  } else if (round.mode === "album") {
    albumImage.src = round.prompt.image_url;
  } else if (round.mode === "finish") {
    lyricsBox.textContent = getFinishPromptText(round.prompt);
    updateFinishContextUI(round.prompt);
  }

  setSubmitState(false);
  if (round.mode === "finish") {
    lyricInput.focus();
  } else {
    songInput.focus();
  }
}

function buildStartPayload() {
  const payload = {
    mode: currentMode,
    session_type: currentSessionType,
  };

  if (currentSessionType === "arcade") {
    payload.round_limit = Number(arcadeCount.value);
  }

  if (currentSessionType === "timed") {
    payload.duration_seconds = Number(timedDuration.value);
  }

  return payload;
}

async function startSession() {
  resetPrompt(modeConfig[currentMode].loading);
  clearFeedback();
  showView("game");
  applyModeChrome(currentMode);
  setLoading(true, modeConfig[currentMode].loading);
  stopTimer();
  currentSessionId = null;

  try {
    const response = await fetch("/api/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildStartPayload()),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Could not start the run.");
    }

    currentSessionId = data.session_id;
    renderRound(data.round);
  } catch (error) {
    setResult(error.message, "fail");
    resetPrompt("Something went wrong starting the round.");
  } finally {
    setLoading(false);
  }
}

function formatBreakdown(breakdown) {
  if (!breakdown) {
    return "";
  }

  if (currentMode === "album") {
    const parts = [];
    parts.push(`Song: ${breakdown.song ? "yes" : "no"}`);
    parts.push(`Album: ${breakdown.album ? "yes" : "no"}`);
    parts.push(`Artist: ${breakdown.artist ? "yes" : "no"}`);
    if (breakdown.combo_bonus) {
      parts.push(`Combo bonus: +${breakdown.combo_bonus}`);
    }
    return parts.join(" | ");
  }

  if (currentMode === "finish") {
    return `Lyric: ${breakdown.lyric ? "yes" : "no"}`;
  }

  return `Song: ${breakdown.song ? "yes" : "no"} | Artist: ${breakdown.artist ? "yes" : "no"}`;
}

async function submitGuess(event) {
  event.preventDefault();
  if (!currentSessionId) {
    setResult("Pick a mode to start.", "fail");
    return;
  }
  if (!hasAnyGuess()) {
    setResult("Type at least one guess first.", "fail");
    return;
  }

  setSubmitState(true, "Checking...");

  try {
    const response = await fetch("/api/session/guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        song_name: songInput.value,
        album_name: albumInput.value,
        lyric: lyricInput.value,
        artist: artistInput.value,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Could not check the guess.");
    }

    let previousRoundSummary = null;
    if (data.round_result) {
      const statusClass = data.round_result.success ? "success" : "fail";
      previousRoundSummary = {
        result: `${data.round_result.message} +${data.round_result.points_awarded}`,
        statusClass,
        answer: currentMode === "finish"
          ? `Answer: ${data.round_result.answer.full_line}`
          : `Last answer: ${data.round_result.answer.song_name} | ${data.round_result.answer.album_name || "Unknown album"} | ${data.round_result.answer.artist}`,
        breakdown: formatBreakdown(data.round_result.breakdown),
      };
      setResult(previousRoundSummary.result, statusClass);
      answerMessage.textContent = previousRoundSummary.answer;
      breakdownMessage.textContent = previousRoundSummary.breakdown;
    }

    setProgress(data.progress || { score: data.score, round_index: 0 });
    if (data.progress) {
      syncTimer(data.progress.time_remaining ?? null);
    }

    if (data.finished || !data.next_round) {
      currentSessionId = null;
      currentRound = null;
      setSubmitState(true, "Run Complete");
      if (!data.round_result) {
        setResult("Run complete.", "success");
        answerMessage.textContent = `Final score: ${data.score}`;
      } else {
        breakdownMessage.textContent = `${breakdownMessage.textContent} | Final score: ${data.score}`;
      }
      return;
    }

    renderRound(data.next_round);
    if (previousRoundSummary) {
      setResult(previousRoundSummary.result, previousRoundSummary.statusClass);
      answerMessage.textContent = previousRoundSummary.answer;
      breakdownMessage.textContent = previousRoundSummary.breakdown;
    }
  } catch (error) {
    setResult(error.message, "fail");
    setSubmitState(false);
  }
}

modeCards.forEach((card) => {
  card.addEventListener("click", () => {
    currentMode = card.dataset.mode;
    startSession();
  });
});

sessionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentSessionType = button.dataset.sessionType;
    updateSetupControls();
  });
});

backButton.addEventListener("click", () => {
  stopTimer();
  currentSessionId = null;
  currentRound = null;
  resetPrompt(modeConfig[currentMode].empty);
  showView("home");
});

playButton.addEventListener("click", startSession);
guessForm.addEventListener("submit", submitGuess);
revealContextButton.addEventListener("click", () => {
  if (!currentRound || currentRound.mode !== "finish") {
    return;
  }

  const totalContext = (currentRound.prompt.context_lines || []).length;
  if (revealedContextCount >= totalContext) {
    return;
  }

  revealedContextCount += 1;
  lyricsBox.textContent = getFinishPromptText(currentRound.prompt);
  updateFinishContextUI(currentRound.prompt);
});

updateSetupControls();
applyModeChrome(currentMode);
resetPrompt(modeConfig[currentMode].empty);
