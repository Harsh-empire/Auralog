(function(){
  const PROFILE_STORAGE_KEY = 'futurereg-profile';
  const THEME_STORAGE_KEY = 'futurereg-theme';
  const CODE_THEME_STORAGE_KEY = 'futurereg-code-theme';
  const DASH_SECTION_KEY = 'futurereg-active-section';
  const THEMES = ['default', 'dark', 'neon', 'aurora', 'void', 'sunset'];
  const CODE_THEMES = ['monokai', 'github', 'dracula'];

  const progressFeed = document.getElementById('progressFeed');
  const projectFeed = document.getElementById('projectFeed');
  const doubtFeed = document.getElementById('doubtFeed');
  const statsContainer = document.getElementById('progressStats');
  const toast = document.getElementById('dashToast');
  const profileTokenHint = document.getElementById('profileTokenHint');
  const profileForm = document.getElementById('profileForm');
  const settingsForm = document.getElementById('settingsForm');
  const progressForm = document.getElementById('progressForm');
  const projectForm = document.getElementById('projectForm');
  const doubtForm = document.getElementById('doubtForm');
  const deckTabs = document.querySelectorAll('.dashboard-tab');
  const deckSections = document.querySelectorAll('.deck-section');

  function activateSection(targetId, animate = true){
    if(!deckSections.length) return;
    const sectionIds = Array.from(deckSections, (section)=>section.dataset.section);
    let resolvedId = targetId && sectionIds.includes(targetId) ? targetId : 'projects';

    deckSections.forEach((section)=>{
      const matches = section.dataset.section === resolvedId;
      if(matches){
        section.style.display = 'flex';
        if(!section.classList.contains('is-active')){
          if(animate){
            section.classList.add('is-animating');
            section.addEventListener('animationend', ()=>section.classList.remove('is-animating'), {once:true});
          }
        }
        section.classList.add('is-active');
      }else if(section.classList.contains('is-active')){
        section.classList.remove('is-active', 'is-animating');
        section.style.display = 'none';
      }else{
        section.style.display = section.style.display || 'none';
      }
    });

    deckTabs.forEach((tab)=>{
      const isActive = tab.dataset.target === resolvedId;
      tab.classList.toggle('active', isActive);
    });

    try{
      localStorage.setItem(DASH_SECTION_KEY, resolvedId);
    }catch(err){ /* ignore storage issues */ }
  }

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

  function loadProfile(){
    try{
      const raw = localStorage.getItem(PROFILE_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    }catch(err){
      return null;
    }
  }

  function persistProfile(profile){
    if(!profile) return;
    let clone;
    try{
      clone = JSON.parse(JSON.stringify(profile));
    }catch(err){
      clone = {...profile};
    }
    savedProfile = clone;
    try{
      localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(clone));
      if(clone.theme) localStorage.setItem(THEME_STORAGE_KEY, clone.theme);
      if(clone.code_theme) localStorage.setItem(CODE_THEME_STORAGE_KEY, clone.code_theme);
    }catch(err){ /* ignore */ }
  }

  function applyTheme(theme, persistLocal=true){
    const normalized = THEMES.includes(theme) ? theme : 'default';
    document.body.classList.remove(...THEMES.map((value)=>`theme-${value}`));
    document.body.classList.add(`theme-${normalized}`);
    if(persistLocal){
      try{ localStorage.setItem(THEME_STORAGE_KEY, normalized); }catch(err){ /* ignore */ }
      if(savedProfile){
        persistProfile({...savedProfile, theme: normalized});
      }
    }
  }

  function applyCodeTheme(theme, persistLocal=true){
    const normalized = CODE_THEMES.includes(theme) ? theme : 'monokai';
    document.body.classList.remove('code-theme-monokai','code-theme-github','code-theme-dracula');
    document.body.classList.add(`code-theme-${normalized}`);
    if(persistLocal){
      try{ localStorage.setItem(CODE_THEME_STORAGE_KEY, normalized); }catch(err){ /* ignore */ }
      if(savedProfile){
        persistProfile({...savedProfile, code_theme: normalized});
      }
    }
  }

  function showToast(msg, ok=true){
    if(!toast) return;
    toast.textContent = msg;
    toast.classList.remove('hidden');
    toast.style.borderColor = ok ? 'rgba(78,238,234,0.16)' : 'rgba(255,104,104,0.24)';
    setTimeout(()=>toast.classList.add('hidden'), 3600);
  }

  function updateTokenHint(){
    if(!profileTokenHint) return;
    if(savedProfile && savedProfile.token){
      const token = String(savedProfile.token);
      const shortened = token.length > 10 ? `${token.slice(0,6)}…${token.slice(-4)}` : token;
      profileTokenHint.textContent = `Device token: ${shortened}. Keep this safe to edit your profile.`;
    }else{
      profileTokenHint.textContent = 'Register to issue a profile token. It stays on this device for quick edits.';
    }
  }

  if(deckSections.length){
    deckSections.forEach((section)=>{
      section.style.display = section.classList.contains('is-active') ? 'flex' : 'none';
    });
    let initialSection = 'projects';
    try{
      const stored = localStorage.getItem(DASH_SECTION_KEY);
      if(stored){
        initialSection = stored;
      }
    }catch(err){ /* ignore */ }
    activateSection(initialSection, false);
    deckTabs.forEach((tab)=>{
      tab.addEventListener('click', ()=>{
        activateSection(tab.dataset.target, true);
      });
    });
  }

  function hydrateProfileForm(profile){
    if(!profile) return;
    if(profileForm){
      const setValue = (name, value='')=>{
        const field = profileForm.elements[name];
        if(field){ field.value = value || ''; }
      };
      setValue('username', profile.username || '');
      setValue('fullName', profile.fullName || '');
      if(profileForm.elements.bio){ profileForm.elements.bio.value = profile.bio || ''; }
      setValue('avatar', profile.avatar || '');
      setValue('github', profile.github || '');
      setValue('linkedin', profile.linkedin || '');
      setValue('website', profile.website || '');
    }

    if(settingsForm){
      const themeField = settingsForm.elements.theme;
      const codeThemeField = settingsForm.elements.code_theme;
      if(themeField){ themeField.value = THEMES.includes(profile.theme) ? profile.theme : 'default'; }
      if(codeThemeField){ codeThemeField.value = CODE_THEMES.includes(profile.code_theme) ? profile.code_theme : 'monokai'; }
      if(settingsForm.elements.public_profile){ settingsForm.elements.public_profile.checked = profile.public_profile !== false; }
      if(settingsForm.elements.email_visible){ settingsForm.elements.email_visible.checked = !!profile.email_visible; }
      const notifications = profile.notifications || {};
      if(settingsForm.elements.notify_progress){ settingsForm.elements.notify_progress.checked = !!notifications.progress; }
      if(settingsForm.elements.notify_projects){ settingsForm.elements.notify_projects.checked = !!notifications.projects; }
      if(settingsForm.elements.notify_doubts){ settingsForm.elements.notify_doubts.checked = !!notifications.doubts; }
    }
  }

  function prefillUserFields(profile){
    if(!profile) return;
    const username = profile.username || '';
    if(progressForm && progressForm.elements.username){ progressForm.elements.username.value = username; }
    if(doubtForm && doubtForm.elements.username){ doubtForm.elements.username.value = username; }
    if(projectForm && projectForm.elements.owner && !projectForm.elements.owner.value){
      projectForm.elements.owner.value = username || profile.fullName || '';
    }
  }

  function renderProgress(items, stats){
    if(!progressFeed) return;
    progressFeed.innerHTML = '';
    if(!items || items.length === 0){
      const empty = document.createElement('div');
      empty.className = 'feed-empty';
      empty.textContent = 'No progress updates yet. Share your first milestone!';
      progressFeed.appendChild(empty);
    }else{
      const statusLabels = {
        'in-progress': 'In Progress',
        'needs-review': 'Needs Review',
        'blocked': 'Blocked',
        'complete': 'Complete'
      };
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

      if(item.responses && item.responses.length){
        const responseList = document.createElement('div');
        responseList.className = 'doubt-responses';
        item.responses.forEach((resp)=>{
          const bubble = document.createElement('div');
          bubble.className = 'doubt-response';
          bubble.innerHTML = `<strong>${resp.is_ai ? 'AuraLog AI' : resp.responder}</strong><span>${new Date(resp.created_at).toLocaleString()}</span><p>${resp.message}</p>`;
          responseList.appendChild(bubble);
        });
        block.appendChild(responseList);
      }

      doubtFeed.appendChild(block);
    });
  }

  function renderProjects(items){
    if(!projectFeed) return;
    projectFeed.innerHTML = '';
    if(!items || items.length === 0){
      const empty = document.createElement('div');
      empty.className = 'feed-empty';
      empty.textContent = 'No projects published yet. Share your build!';
      projectFeed.appendChild(empty);
      return;
    }

    items.forEach((item)=>{
      const card = document.createElement('article');
      card.className = 'project-card';

      const header = document.createElement('header');
      const h3 = document.createElement('h3');
      h3.textContent = item.title;
      const owner = document.createElement('div');
      owner.className = 'project-meta';
      const meta = item.metadata || {};
      const snippetCount = typeof meta.snippet_count === 'number' ? meta.snippet_count : (item.snippets ? item.snippets.length : 0);
      const ownerBits = [
        `By <strong>@${item.owner}</strong>`,
        new Date(item.created_at).toLocaleDateString()
      ];
      if(item.repo_url){ ownerBits.push(`<a href="${item.repo_url}" target="_blank" rel="noopener">repo</a>`); }
      if(snippetCount){ ownerBits.push(`${snippetCount} snippet${snippetCount === 1 ? '' : 's'}`); }
      owner.innerHTML = ownerBits.join(' · ');
      header.appendChild(h3);
      header.appendChild(owner);
      card.appendChild(header);

      const summary = document.createElement('div');
      summary.className = 'project-ai-summary';
      summary.textContent = item.ai_summary || item.summary || 'No summary yet';
      card.appendChild(summary);

      if(item.tags && item.tags.length){
        const tagRow = document.createElement('div');
        tagRow.className = 'project-tags';
        item.tags.forEach((tag)=>{
          const chip = document.createElement('span');
          chip.className = 'project-tag';
          chip.textContent = tag;
          tagRow.appendChild(chip);
        });
        card.appendChild(tagRow);
      }

      if(item.snippets && item.snippets.length){
        item.snippets.forEach((snippet)=>{
          const wrapper = document.createElement('div');
          wrapper.className = 'snippet-block';
          const snippetMeta = document.createElement('div');
          snippetMeta.className = 'snippet-meta';
          snippetMeta.innerHTML = `<span>${snippet.title || 'Snippet'}</span><span>${snippet.language || 'plain text'}</span>`;
          const pre = document.createElement('pre');
          pre.textContent = snippet.code;
          wrapper.appendChild(snippetMeta);
          wrapper.appendChild(pre);
          if(snippet.notes){
            const notes = document.createElement('p');
            notes.style.marginTop = '8px';
            notes.style.color = '#9dbcff';
            notes.style.fontSize = '12px';
            notes.textContent = snippet.notes;
            wrapper.appendChild(notes);
          }
          card.appendChild(wrapper);
        });
      }

      projectFeed.appendChild(card);
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

  async function loadProjects(){
    try{
      const resp = await fetch(`${API_BASE}/api/projects`);
      if(!resp.ok) throw new Error('fetch failed');
      const data = await resp.json();
      if(!data.success) throw new Error('failed');
      renderProjects(data.items);
    }catch(err){
      console.error(err);
      renderProjects([]);
      showToast('Could not load projects', false);
    }
  }

  async function refreshProfileFromServer(){
    if(!savedProfile || !savedProfile.username || !savedProfile.token) return;
    try{
      const url = new URL(`${API_BASE}/api/profile/${encodeURIComponent(savedProfile.username)}`);
      url.searchParams.set('token', savedProfile.token);
      const resp = await fetch(url.toString());
      if(!resp.ok) return;
      const data = await resp.json();
      if(!data.success) return;
      const merged = {...savedProfile, ...data.profile, token: savedProfile.token};
      persistProfile(merged);
      hydrateProfileForm(merged);
      prefillUserFields(merged);
      if(merged.theme){ applyTheme(merged.theme, true); }
      if(merged.code_theme){ applyCodeTheme(merged.code_theme, true); }
      updateTokenHint();
    }catch(err){
      console.error(err);
    }
  }

  function getCheckbox(form, name){
    return form && form.elements[name] ? !!form.elements[name].checked : false;
  }

  function readField(form, name){
    if(!form || !form.elements[name] || typeof form.elements[name].value !== 'string') return '';
    return form.elements[name].value.trim();
  }

  function collectProfileUpdates(){
    const updates = {
      fullName: readField(profileForm, 'fullName'),
      bio: profileForm && profileForm.elements.bio && typeof profileForm.elements.bio.value === 'string' ? profileForm.elements.bio.value.trim() : '',
      avatar: readField(profileForm, 'avatar'),
      github: readField(profileForm, 'github'),
      linkedin: readField(profileForm, 'linkedin'),
      website: readField(profileForm, 'website')
    };

    let themeValue = readField(settingsForm, 'theme') || 'default';
    if(!THEMES.includes(themeValue)) themeValue = 'default';
    let codeThemeValue = readField(settingsForm, 'code_theme') || 'monokai';
    if(!CODE_THEMES.includes(codeThemeValue)) codeThemeValue = 'monokai';

    updates.theme = themeValue;
    updates.code_theme = codeThemeValue;
    updates.public_profile = getCheckbox(settingsForm, 'public_profile');
    updates.email_visible = getCheckbox(settingsForm, 'email_visible');
    updates.notifications = {
      progress: getCheckbox(settingsForm, 'notify_progress'),
      projects: getCheckbox(settingsForm, 'notify_projects'),
      doubts: getCheckbox(settingsForm, 'notify_doubts')
    };

    return updates;
  }

  function currentUsername(){
    if(profileForm && profileForm.elements.username){
      const raw = profileForm.elements.username.value;
      if(typeof raw === 'string' && raw.trim()){ return raw.trim(); }
    }
    if(savedProfile && typeof savedProfile.username === 'string' && savedProfile.username.trim()){
      return savedProfile.username.trim();
    }
    return '';
  }

  async function saveProfileUpdates(){
    const username = currentUsername();
    if(!username){
      showToast('Enter your username in the registration page first', false);
      return;
    }

    const token = savedProfile && savedProfile.token ? savedProfile.token : '';
    if(!token){
      showToast('Profile updates need your device token. Register again if you lost it.', false);
      return;
    }

    const updates = collectProfileUpdates();

    try{
      const resp = await fetch(`${API_BASE}/api/profile/${encodeURIComponent(username)}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token, updates})
      });
      const data = await resp.json();
      if(!resp.ok || !data.success) throw new Error(data.error || 'failed');
      const merged = {...(savedProfile || {}), ...data.profile, token};
      persistProfile(merged);
      hydrateProfileForm(merged);
      prefillUserFields(merged);
      applyTheme(merged.theme || 'default', true);
      applyCodeTheme(merged.code_theme || 'monokai', true);
      updateTokenHint();
      showToast('Profile saved');
    }catch(err){
      console.error(err);
      showToast('Could not save profile', false);
    }
  }

  const API_BASE = resolveApiBase();
  try{
    const qp = new URLSearchParams(window.location.search);
    if(qp.get('api')){
      localStorage.setItem('futurereg-api-base', API_BASE);
    }
  }catch(err){ /* ignore */ }

  let savedProfile = loadProfile();
  const initialTheme = (savedProfile && savedProfile.theme) || localStorage.getItem(THEME_STORAGE_KEY) || 'default';
  applyTheme(initialTheme, false);
  const initialCodeTheme = (savedProfile && savedProfile.code_theme) || localStorage.getItem(CODE_THEME_STORAGE_KEY) || 'monokai';
  applyCodeTheme(initialCodeTheme, false);

  if(!progressFeed && !projectFeed && !doubtFeed && !profileForm){
    updateTokenHint();
    return;
  }

  if(savedProfile){
    hydrateProfileForm(savedProfile);
    prefillUserFields(savedProfile);
  }
  updateTokenHint();

  if(profileForm){
    profileForm.addEventListener('submit', (ev)=>{
      ev.preventDefault();
      saveProfileUpdates();
    });
  }

  if(settingsForm){
    settingsForm.addEventListener('submit', (ev)=>{
      ev.preventDefault();
      saveProfileUpdates();
    });
    if(settingsForm.elements.theme){
      settingsForm.elements.theme.addEventListener('change', (ev)=>{
        applyTheme(ev.target.value, false);
      });
    }
    if(settingsForm.elements.code_theme){
      settingsForm.elements.code_theme.addEventListener('change', (ev)=>{
        applyCodeTheme(ev.target.value, false);
      });
    }
  }

  if(progressForm){
    progressForm.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const formData = new FormData(progressForm);
      const payload = Object.fromEntries(formData.entries());
      try{
        const resp = await fetch(`${API_BASE}/api/progress`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(payload)
        });
        const data = await resp.json();
        if(!resp.ok || !data.success) throw new Error(data.error || 'request failed');
        progressForm.reset();
        prefillUserFields(savedProfile);
        showToast('Progress update shared with mentors');
        loadProgress();
      }catch(err){
        console.error(err);
        showToast('Could not save progress update', false);
      }
    });
  }

  if(doubtForm){
    doubtForm.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const formData = new FormData(doubtForm);
      const payload = Object.fromEntries(formData.entries());
      try{
        const resp = await fetch(`${API_BASE}/api/doubts`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(payload)
        });
        const data = await resp.json();
        if(!resp.ok || !data.success) throw new Error(data.error || 'request failed');
        doubtForm.reset();
        prefillUserFields(savedProfile);
        showToast('Question submitted for review');
        loadDoubts();
      }catch(err){
        console.error(err);
        showToast('Could not submit question', false);
      }
    });
  }

  if(projectForm){
    if(savedProfile && projectForm.elements.owner && !projectForm.elements.owner.value){
      projectForm.elements.owner.value = savedProfile.username || savedProfile.fullName || '';
    }
    projectForm.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const formData = new FormData(projectForm);
      const payload = Object.fromEntries(formData.entries());
      try{
        const resp = await fetch(`${API_BASE}/api/projects`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(payload)
        });
        const data = await resp.json();
        if(!resp.ok || !data.success) throw new Error(data.error || 'request failed');
        projectForm.reset();
        prefillUserFields(savedProfile);
        showToast('Project published to the AuraLog library');
        loadProjects();
      }catch(err){
        console.error(err);
        showToast('Could not publish project', false);
      }
    });
  }

  loadProgress();
  loadDoubts();
  loadProjects();
  refreshProfileFromServer();
})();
