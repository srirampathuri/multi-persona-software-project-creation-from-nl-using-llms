document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('ideaForm');
    const spinner = document.getElementById('spinner');
    const progressBar = document.getElementById('progress-bar');
    const timeline = document.getElementById('status-timeline');
    const downloadBtn = document.getElementById('download-btn');
    const generateBtn = form.querySelector('button[type="submit"]');
    let interval = null;

    function resetUI() {
        timeline.innerHTML = '';
        progressBar.style.width = '0%';
        progressBar.textContent = 'Waiting...';
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-primary';
        spinner.classList.add('d-none');
        downloadBtn.style.display = 'none';
        generateBtn.disabled = false;
    }

    function showLatestStatus(message, type) {
        timeline.innerHTML = '';
        const li = document.createElement('li');
        li.className = typeClass(type);
        li.textContent = message;
        timeline.appendChild(li);
    }

    function typeClass(type) {
        if (type === 'success') return 'success';
        if (type === 'error') return 'error';
        if (type === 'complete') return 'complete';
        return 'info';
    }

    function updateProgressBar(status, type) {
        let percent = 10;
        if (/System Design/i.test(status)) percent = 30;
        else if (/Break/i.test(status)) percent = 45;
        else if (/code files/i.test(status)) percent = 60;
        else if (/unit tests/i.test(status)) percent = 75;
        else if (/tests and fixing/i.test(status)) percent = 85;
        else if (/complete|success/i.test(status)) percent = 100;
        progressBar.style.width = percent + '%';
        progressBar.textContent = status;
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-primary';
        if (type === 'error') progressBar.classList.add('bg-danger');
        if (type === 'success') progressBar.classList.add('bg-success');
        if (type === 'complete') progressBar.classList.add('bg-warning');
    }

    function statusType(status) {
        if (/saved to|generated|updated by Code Fixer|Tests passed/i.test(status)) return 'success';
        if (/Could not fix|Failed|error/i.test(status)) return 'error';
        if (/complete/i.test(status)) return 'complete';
        return 'info';
    }

    form.onsubmit = function(e) {
        e.preventDefault();
        resetUI();
        spinner.classList.remove('d-none');
        generateBtn.disabled = true;
        const idea = this.idea.value;
        fetch('/start', {
            method: 'POST',
            body: new URLSearchParams({ idea }),
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })
        .then(res => res.json())
        .then(data => {
            const sessionId = data.session_id;
            interval = setInterval(() => {
                fetch('/status/' + sessionId)
                    .then(res => res.json())
                    .then(statusData => {
                        let status = statusData.status || 'Processing...';
                        let type = statusType(status);
                        showLatestStatus(status, type);
                        updateProgressBar(status, type);
                        if (statusData.download_url) {
                            downloadBtn.href = statusData.download_url;
                            downloadBtn.style.display = 'block';
                        }
                        if (/complete|error|Could not fix|Failed|success/i.test(status)) {
                            spinner.classList.add('d-none');
                            clearInterval(interval);
                            generateBtn.disabled = false;
                        }
                    });
            }, 2000);
        });
    };

    // Reset UI on load
    resetUI();
}); 