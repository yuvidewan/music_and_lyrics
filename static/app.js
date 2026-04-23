const homeView = document.querySelector("#home");
const gameView = document.querySelector("#game");
const lyricTile = document.querySelector("#guess-lyric-tile");
const songTile = document.querySelector("#guess-song-tile");
const backButton = document.querySelector("#back-button");
const playButton = document.querySelector("#play-button");
const submitButton = document.querySelector("#submit-button");
const lyricsBox = document.querySelector("#lyrics-box");
const audioBox = document.querySelector("#audio-box");
const audioPlayer = document.querySelector("#audio-player");
const promptTitle = document.querySelector("#prompt-title");
const gameTitle = document.querySelector("#game-title");
const guessForm = document.querySelector("#guess-form");
const songInput = document.querySelector("#song-input");
const artistInput = document.querySelector("#artist-input");
const resultMessage = document.querySelector("#result-message");
const answerMessage = document.querySelector("#answer-message");

let currentGameId = null;
let currentMode = "lyrics";

function showView(viewName) {
  homeView.classList.toggle("active", viewName === "home");
  gameView.classList.toggle("active", viewName === "game");
}

function setResult(message, status) {
  resultMessage.textContent = message;
  resultMessage.className = "result-message";
  if (status) {
    resultMessage.classList.add(status);
  }
}

function resetRound() {
  currentGameId = null;
  songInput.value = "";
  artistInput.value = "";
  submitButton.disabled = true;
  answerMessage.textContent = "";
  audioPlayer.removeAttribute("src");
  audioPlayer.load();
  setResult("", "");
}

function openMode(mode) {
  currentMode = mode;
  resetRound();

  if (mode === "song") {
    gameTitle.textContent = "Guess the Song";
    promptTitle.textContent = "Preview";
    lyricsBox.classList.add("hidden");
    audioBox.classList.remove("hidden");
  } else {
    gameTitle.textContent = "Guess the Lyric";
    promptTitle.textContent = "Lyrics";
    lyricsBox.classList.remove("hidden");
    audioBox.classList.add("hidden");
    lyricsBox.textContent = "Press Play to load a random song from your playlist.";
  }

  showView("game");
}

async function startRound() {
  resetRound();
  playButton.disabled = true;

  if (currentMode === "song") {
    lyricsBox.textContent = "";
    setResult("Loading preview...", "");
  } else {
    lyricsBox.textContent = "Loading lyrics...";
  }

  try {
    const endpoint = currentMode === "song" ? "/api/song/start" : "/api/game/start";
    const response = await fetch(endpoint, { method: "POST" });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Could not start the round.");
    }

    currentGameId = data.game_id;

    if (currentMode === "song") {
      audioPlayer.src = data.preview_url;
      audioPlayer.load();
      setResult("", "");
    } else {
      lyricsBox.textContent = data.lyrics;
    }

    submitButton.disabled = false;
    songInput.focus();
  } catch (error) {
    if (currentMode === "lyrics") {
      lyricsBox.textContent = "Something went wrong while loading lyrics.";
    }
    setResult(error.message, "fail");
  } finally {
    playButton.disabled = false;
  }
}

async function submitGuess(event) {
  event.preventDefault();
  if (!currentGameId) {
    setResult("Press Play first.", "fail");
    return;
  }

  submitButton.disabled = true;
  setResult("Checking...", "");
  answerMessage.textContent = "";

  try {
    const response = await fetch("/api/game/guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        game_id: currentGameId,
        song_name: songInput.value,
        artist: artistInput.value,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Could not check the guess.");
    }

    if (data.success) {
      setResult(data.message, "success");
      currentGameId = null;
    } else {
      setResult(data.message, "fail");
      submitButton.disabled = false;
    }

    answerMessage.textContent = `Answer: ${data.answer.song_name} by ${data.answer.artist}`;
  } catch (error) {
    setResult(error.message, "fail");
    submitButton.disabled = false;
  }
}

lyricTile.addEventListener("click", () => openMode("lyrics"));
songTile.addEventListener("click", () => openMode("song"));
backButton.addEventListener("click", () => showView("home"));
playButton.addEventListener("click", startRound);
guessForm.addEventListener("submit", submitGuess);
