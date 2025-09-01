let currentSong = null;

// Song playback
function playSong(song) {
    const status = document.getElementById('player-status');
    const player = document.getElementById('audioPlayer');

    if (currentSong && currentSong !== song) {
        player.pause();
    }

    currentSong = song;
    status.textContent = 'Loading...';
    player.src = `/play/${encodeURIComponent(song)}`;
    player.play();

    player.oncanplay = () => {
        status.textContent = `Now Playing: ${song}`;
    };
}

// Song download
document.getElementById('search-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const query = this.querySelector('input[name="query"]').value;
    const status = document.getElementById('status-container');
    
    status.innerHTML = `<div class="download-info">Downloading "${query}"...</div>`;

    fetch('/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `query=${encodeURIComponent(query)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.task_id) {
            checkDownloadStatus(data.task_id);
        }
    });
});

function checkDownloadStatus(taskId) {
    const status = document.getElementById('status-container');
    const interval = setInterval(() => {
        fetch(`/download_status/${taskId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'complete') {
                    clearInterval(interval);
                    status.innerHTML = '<div class="download-info success">Download complete!</div>';
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            });
    }, 2000);

    setTimeout(() => clearInterval(interval), 60000);
}

// Playlist functions
function showCreatePlaylistModal() {
    document.querySelector('.modal-overlay').style.display = 'block';
    document.querySelector('.playlist-modal').style.display = 'block';
}

function hideCreatePlaylistModal() {
    document.querySelector('.modal-overlay').style.display = 'none';
    document.querySelector('.playlist-modal').style.display = 'none';
    document.getElementById('playlist-name').value = '';
}

function createPlaylist() {
    const name = document.getElementById('playlist-name').value;
    if (!name) {
        showNotification('Please enter a name', 'error');
        return;
    }

    fetch('/playlist/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `name=${encodeURIComponent(name)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Playlist created');
            hideCreatePlaylistModal();
            window.location.reload();
        }
    });
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

document.querySelector('.modal-overlay').addEventListener('click', hideCreatePlaylistModal);
