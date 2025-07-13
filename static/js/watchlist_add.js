// Enhanced Add to Watchlist: Choose destination (personal or group)
document.addEventListener('DOMContentLoaded', function() {
    const watchlistBtn = document.querySelector('.btn-watchlist');
    if (!watchlistBtn) return;

    watchlistBtn.addEventListener('click', function() {
        const isAuthenticated = this.dataset.authenticated === 'true';
        if (!isAuthenticated) {
            showLoginPrompt();
            return;
        }
        showAddToWatchlistModal(this.dataset.tmdbId, this.dataset.contentType);
    });

    function showAddToWatchlistModal(tmdbId, contentType) {
        // Create modal if not exists
        let modal = document.getElementById('addToWatchlistModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'addToWatchlistModal';
            modal.className = 'modal fade';
            modal.tabIndex = -1;
            modal.innerHTML = `
<div class="modal-dialog modal-dialog-centered">
  <div class="modal-content bg-dark text-light">
    <div class="modal-header">
      <h5 class="modal-title">Add to Watchlist</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
    </div>
    <div class="modal-body">
      <div class="mb-3">
        <label class="form-label">Where do you want to add this?</label>
        <select class="form-select" id="watchlist-destination">
          <option value="personal">My Watchlist</option>
          <option value="group">A Group Watchlist</option>
        </select>
      </div>
      <div class="mb-3 d-none" id="group-select-row">
        <label class="form-label">Select Group</label>
        <select class="form-select" id="group-select"></select>
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
      <button type="button" class="btn btn-primary" id="add-to-destination-btn">Add</button>
    </div>
  </div>
</div>`;
            document.body.appendChild(modal);
        }
        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Populate group list if needed
        const destinationSelect = modal.querySelector('#watchlist-destination');
        const groupRow = modal.querySelector('#group-select-row');
        const groupSelect = modal.querySelector('#group-select');
        destinationSelect.value = 'personal';
        groupRow.classList.add('d-none');
        groupSelect.innerHTML = '';

        destinationSelect.addEventListener('change', function() {
            if (this.value === 'group') {
                groupRow.classList.remove('d-none');
                fetch('/groups/user-groups')
                    .then(res => res.json())
                    .then(data => {
                        groupSelect.innerHTML = '';
                        if (data.groups && data.groups.length) {
                            data.groups.forEach(g => {
                                const opt = document.createElement('option');
                                opt.value = g.id;
                                opt.textContent = g.name;
                                groupSelect.appendChild(opt);
                            });
                        } else {
                            const opt = document.createElement('option');
                            opt.value = '';
                            opt.textContent = 'No groups found';
                            groupSelect.appendChild(opt);
                        }
                    });
            } else {
                groupRow.classList.add('d-none');
            }
        });

        // Add button logic
        modal.querySelector('#add-to-destination-btn').onclick = function() {
            if (destinationSelect.value === 'personal') {
                addToPersonalWatchlist(tmdbId, contentType);
                bsModal.hide();
            } else if (destinationSelect.value === 'group') {
                const groupId = groupSelect.value;
                if (!groupId) {
                    alert('Please select a group.');
                    return;
                }
                addToGroupWatchlist(tmdbId, contentType, groupId);
                bsModal.hide();
            }
        };
    }

    function addToPersonalWatchlist(tmdbId, contentType) {
        fetch('/content/watchlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrf_token || document.querySelector('input[name=csrf_token]')?.value
            },
            body: JSON.stringify({ tmdb_id: tmdbId, content_type: contentType, status: 'want_to_watch' })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) location.reload();
            else alert('Error: ' + (data.error || 'Could not add to watchlist.'));
        });
    }

    function addToGroupWatchlist(tmdbId, contentType, groupId) {
        fetch(`/groups/${groupId}/add_from_tmdb`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrf_token || document.querySelector('input[name=csrf_token]')?.value
            },
            body: JSON.stringify({ tmdb_id: tmdbId, content_type: contentType })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) window.location.href = `/watchlist/group/${groupId}`;
            else alert('Error: ' + (data.error || 'Could not add to group watchlist.'));
        });
    }

    function showLoginPrompt() {
        const message = 'Sign up or log in to add this to your watchlist!';
        if (confirm(message + '\n\nClick OK to go to login page, Cancel to register.')) {
            window.location.href = '/auth/login';
        } else {
            window.location.href = '/auth/register';
        }
    }
});
