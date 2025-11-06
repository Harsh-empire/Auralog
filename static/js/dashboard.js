(function(){
  const progressFeed = document.getElementById('progressFeed');
  const doubtFeed = document.getElementById('doubtFeed');
  const statsContainer = document.getElementById('progressStats');
  const toast = document.getElementById('dashToast');
  const progressForm = document.getElementById('progressForm');
  const doubtForm = document.getElementById('doubtForm');

  function resolveApiBase(){
    const trim = (v)=>typeof v === 'string' ? v.replace(/\/$/, '') : v;
    try{
      const paramBase = new URLSearchParams(window.location.search).get('api');
      if(paramBase) return trim(paramBase);
    }catch(err){ /* ignore parse errors */ }
    if(document.body && document.body.dataset && document.body.dataset.apiBase){
      return trim(document.body.dataset.apiBase);
    }
    if(window.location && window.location.origin && window.location.origin !== 'null'){
      return trim(window.location.origin);
    }
    try{
      const stored = localStorage.getItem('futurereg-api-base');
      if(stored) return trim(stored);
    }catch(err){ /* localStorage unavailable */ }
    return 'http://127.0.0.1:5000';
  }

  const API_BASE = resolveApiBase();
  try{
    const qp = new URLSearchParams(window.location.search);
    if(qp.get('api')){
      localStorage.setItem('futurereg-api-base', API_BASE);
    }
  }catch(err){ /* ignore */ }
  let savedProfile = null;
  try{
    savedProfile = JSON.parse(localStorage.getItem('futurereg-profile') || 'null');
  }catch(err){ savedProfile = null; }

  if(!progressFeed && !doubtFeed) return;

  const statusLabels = {
    'in-progress': 'In Progress',
    'needs-review': 'Needs Review',
    'blocked': 'Blocked',
    'complete': 'Complete'
  };

  function showToast(msg, ok=true){
    if(!toast) return;
    toast.textContent = msg;
    toast.classList.remove('hidden');
    toast.style.borderColor = ok? 'rgba(78,238,234,0.16)' : 'rgba(255,104,104,0.18)';
    setTimeout(()=>toast.classList.add('hidden'), 3600);
  }

  function renderProgress(items, stats){
    if(!progressFeed) return;
    progressFeed.innerHTML = '';
    if(!items || items.length === 0){
      const empty = document.createElement('div');
      empty.className = 'feed-empty';
      empty.textContent = 'No progress updates yet. Share your first milestone!';
      progressFeed.appendChild(empty);
    } else {
      items.forEach((item)=>{
        const card = document.createElement('article');
        card.className = 'panel progress-item';

        const header = document.createElement('header');
        const title = document.createElement('h3');
        title.textContent = item.title;
        const metaTime = document.createElement('time');
        metaTime.dateTime = item.created_at;
        metaTime.textContent = new Date(item.created_at).toLocaleString();
        header.appendChild(title);
        header.appendChild(metaTime);

        const summary = document.createElement('p');
        summary.textContent = item.summary;

        const meta = document.createElement('div');
        meta.className = 'meta';
        const status = document.createElement('span');
        status.className = 'status-pill';
        status.dataset.state = item.status;
        status.textContent = statusLabels[item.status] || item.status;
        meta.appendChild(status);

        const author = document.createElement('span');
        author.className = 'status-pill';
        author.style.background = 'rgba(138,108,255,0.16)';
        author.style.color = '#d8cfff';
        author.textContent = `@${item.username}`;
        meta.appendChild(author);

        if(item.errors){
          const issue = document.createElement('span');
          issue.className = 'issue-chip';
          issue.textContent = item.errors;
          meta.appendChild(issue);
        }

        if(item.blockers){
          const blocker = document.createElement('span');
          blocker.className = 'issue-chip';
          blocker.style.background = 'rgba(255,211,102,0.22)';
          blocker.style.color = '#ffe79a';
          blocker.textContent = item.blockers;
          meta.appendChild(blocker);
        }

        card.appendChild(header);
        card.appendChild(summary);
        card.appendChild(meta);
        progressFeed.appendChild(card);
      });
    }

    if(statsContainer && stats){
      statsContainer.innerHTML = '';
      const total = document.createElement('div');
      total.className = 'stat-card';
      total.innerHTML = `<div class="label">Total Updates</div><div class="value">${stats.total}</div>`;
      statsContainer.appendChild(total);

      const issues = document.createElement('div');
      issues.className = 'stat-card';
      issues.innerHTML = `<div class="label">Updates With Issues</div><div class="value">${stats.withIssues}</div>`;
      statsContainer.appendChild(issues);

      const review = document.createElement('div');
      review.className = 'stat-card';
      review.innerHTML = `<div class="label">Needs Review</div><div class="value">${stats.statusCounts['needs-review'] || 0}</div>`;
      statsContainer.appendChild(review);
    }
  }

  function renderDoubts(items){
    if(!doubtFeed) return;
    doubtFeed.innerHTML = '';
    if(!items || items.length === 0){
      const empty = document.createElement('div');
      empty.className = 'feed-empty';
      empty.textContent = 'No doubts raised yet. Your questions will show here.';
      doubtFeed.appendChild(empty);
      return;
    }

    items.forEach((item)=>{
      const block = document.createElement('article');
      block.className = 'doubt-item';

      const title = document.createElement('h3');
      title.textContent = item.topic || 'Untitled';
      block.appendChild(title);

      const content = document.createElement('p');
      content.textContent = item.question;
      block.appendChild(content);

      const footer = document.createElement('footer');
      const meta = document.createElement('span');
      meta.textContent = `@${item.username}`;
      footer.appendChild(meta);
      const status = document.createElement('span');
      status.className = 'status-pill';
      status.dataset.state = item.resolved ? 'complete' : 'needs-review';
      status.textContent = item.resolved ? 'Resolved' : 'Awaiting reply';
      footer.appendChild(status);
      block.appendChild(footer);

      doubtFeed.appendChild(block);
    });
  }

  async function loadProgress(){
    try{
  const resp = await fetch(`${API_BASE}/api/progress`);
      if(!resp.ok) throw new Error('fetch failed');
      const data = await resp.json();
      if(!data.success) throw new Error('failed');
      renderProgress(data.items, data.stats);
    }catch(err){
      console.error(err);
      renderProgress([], {total:0, withIssues:0, statusCounts:{}});
      showToast('Could not load progress feed', false);
    }
  }

  async function loadDoubts(){
    try{
  const resp = await fetch(`${API_BASE}/api/doubts`);
      if(!resp.ok) throw new Error('fetch failed');
      const data = await resp.json();
      if(!data.success) throw new Error('failed');
      renderDoubts(data.items);
    }catch(err){
      console.error(err);
      renderDoubts([]);
      showToast('Could not load doubts', false);
    }
  }

  if(progressForm){
    if(savedProfile){
      if(progressForm.elements.username){ progressForm.elements.username.value = savedProfile.username || ''; }
      if(progressForm.elements.status && savedProfile.role){
        // optional: preset status for explorers – keep default as in-progress
      }
    }
    progressForm.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const formData = new FormData(progressForm);
      const payload = Object.fromEntries(formData.entries());
      try{
  const resp = await fetch(`${API_BASE}/api/progress`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        const data = await resp.json();
        if(!resp.ok || !data.success) throw new Error(data.error || 'request failed');
        progressForm.reset();
        showToast('Progress update shared with mentors');
        loadProgress();
      }catch(err){
        console.error(err);
        showToast('Could not save progress update', false);
      }
    });
  }

  if(doubtForm){
    if(savedProfile && doubtForm.elements.username){
      doubtForm.elements.username.value = savedProfile.username || '';
    }
    doubtForm.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const formData = new FormData(doubtForm);
      const payload = Object.fromEntries(formData.entries());
      try{
  const resp = await fetch(`${API_BASE}/api/doubts`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        const data = await resp.json();
        if(!resp.ok || !data.success) throw new Error(data.error || 'request failed');
        doubtForm.reset();
        showToast('Question submitted for review');
        loadDoubts();
      }catch(err){
        console.error(err);
        showToast('Could not submit question', false);
      }
    });
  }

  loadProgress();
  loadDoubts();
})();
