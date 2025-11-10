// Simple nebula canvas + form handling
(function(){
  // Nebula background with parallax + mouse tilt for the card
  const canvas = document.getElementById('nebula');
  const ctx = canvas.getContext('2d');
  function resize(){canvas.width = window.innerWidth; canvas.height = window.innerHeight;}
  window.addEventListener('resize', resize); resize();

  const stars=[]; for(let i=0;i<260;i++){stars.push({x:Math.random()*canvas.width,y:Math.random()*canvas.height,r:Math.random()*1.8,alpha:0.2+Math.random()*0.9,ox:0,oy:0});}

  let mouseX = canvas.width/2, mouseY = canvas.height/2;
  window.addEventListener('mousemove', (e)=>{ mouseX = e.clientX; mouseY = e.clientY; document.documentElement.style.setProperty('--mx', (mouseX / window.innerWidth).toString()); document.documentElement.style.setProperty('--my', (mouseY / window.innerHeight).toString()); });

  function draw(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    // shifting gradient
    const t = Date.now()*0.00014;
    const g = ctx.createLinearGradient(Math.sin(t)*canvas.width, Math.cos(t)*canvas.height, canvas.width - Math.sin(t)*canvas.width, canvas.height - Math.cos(t)*canvas.height);
    g.addColorStop(0,'rgba(6,10,26,0.75)'); g.addColorStop(0.5,'rgba(10,18,36,0.6)'); g.addColorStop(1,'rgba(6,8,18,0.85)');
    ctx.fillStyle = g; ctx.fillRect(0,0,canvas.width,canvas.height);

    // moving soft light blobs
    const cx = canvas.width*0.6 + Math.sin(t*1.1)*220 + (mouseX - canvas.width/2)*0.06;
    const cy = canvas.height*0.35 + Math.cos(t*0.9)*140 + (mouseY - canvas.height/2)*0.06;
    const rg = ctx.createRadialGradient(cx,cy,0,cx,cy,900);
    rg.addColorStop(0,'rgba(78,238,234,0.12)'); rg.addColorStop(0.4,'rgba(138,108,255,0.06)'); rg.addColorStop(1,'rgba(10,10,12,0)');
    ctx.globalCompositeOperation='screen'; ctx.fillStyle=rg; ctx.fillRect(0,0,canvas.width,canvas.height);

    // stars with parallax
    ctx.globalCompositeOperation='lighter';
    for(const s of stars){
      // small parallax based on mouse position
      const px = s.x + (mouseX - canvas.width/2) * (s.r*0.002);
      const py = s.y + (mouseY - canvas.height/2) * (s.r*0.002);
      ctx.beginPath(); ctx.fillStyle = `rgba(180,220,255,${Math.min(1, s.alpha*0.7)})`;
      ctx.arc((px + Math.sin(t*1.5+s.r)*6) % canvas.width, (py + Math.cos(t*1.1+s.r)*4) % canvas.height, s.r, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.globalCompositeOperation='source-over';
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);

  // interactive card tilt (uses CSS variables on mouse move over card)
  const card = document.querySelector('.card');
  if(card){
    card.addEventListener('pointermove', (e)=>{
      const r = card.getBoundingClientRect();
      const rx = ( (e.clientY - r.top) - r.height/2 ) / r.height * -12;
      const ry = ( (e.clientX - r.left) - r.width/2 ) / r.width * 14;
      card.style.setProperty('--rx', rx.toFixed(2) + 'deg');
      card.style.setProperty('--ry', ry.toFixed(2) + 'deg');
      card.classList.add('tilt');
    });
    card.addEventListener('pointerleave', ()=>{ card.style.setProperty('--rx','0deg'); card.style.setProperty('--ry','0deg'); card.classList.remove('tilt'); });
  }

  // API host discovery + form handling + toasts + ripple
  function resolveApiBase(){
    const trim = (v)=>typeof v === 'string' ? v.replace(/\/$/, '') : v;
    try {
      const qpBase = new URLSearchParams(window.location.search).get('api');
      if(qpBase) return trim(qpBase);
    } catch (err) {
      /* ignore query parsing issues */
    }
    if(document.body && document.body.dataset && document.body.dataset.apiBase){
      return trim(document.body.dataset.apiBase);
    }
    if(window.location && window.location.origin && window.location.origin !== 'null'){
      return trim(window.location.origin);
    }
    try {
      const stored = localStorage.getItem('futurereg-api-base');
      if(stored) return trim(stored);
    } catch (err) {
      /* localStorage unavailable */
    }
    return 'http://127.0.0.1:5000';
  }

  const API_BASE = resolveApiBase();
  try {
    const qp = new URLSearchParams(window.location.search);
    if(qp.get('api')){
      localStorage.setItem('futurereg-api-base', API_BASE);
    }
  } catch (err) {
    /* ignore */
  }

  const form = document.getElementById('regForm');
  const loginForm = document.getElementById('loginForm');
  const toast = document.getElementById('toast');
  const btn = document.getElementById('submitBtn');
  const PROFILE_KEY = 'futurereg-profile';
  const THEME_STORAGE_KEY = 'futurereg-theme';
  const CODE_THEME_STORAGE_KEY = 'futurereg-code-theme';
  const THEMES = ['default','dark','neon','aurora','void','sunset'];
  const CODE_THEMES = ['monokai','github','dracula'];
  let savedProfile = null;

  function applyBodyTheme(theme){
    const normalized = THEMES.includes(theme) ? theme : 'default';
    document.body.classList.remove(...THEMES.map((value)=>`theme-${value}`));
    document.body.classList.add(`theme-${normalized}`);
  }

  function applyBodyCodeTheme(theme){
    const normalized = CODE_THEMES.includes(theme) ? theme : 'monokai';
    document.body.classList.remove('code-theme-monokai','code-theme-github','code-theme-dracula');
    document.body.classList.add(`code-theme-${normalized}`);
  }

  function readStored(key, fallback){
    try{
      const value = localStorage.getItem(key);
      return value || fallback;
    }catch(err){
      return fallback;
    }
  }
  try {
    savedProfile = JSON.parse(localStorage.getItem(PROFILE_KEY) || 'null');
  } catch (err) {
    savedProfile = null;
  }

  const initialTheme = (savedProfile && savedProfile.theme) || readStored(THEME_STORAGE_KEY, 'default');
  applyBodyTheme(initialTheme);
  const initialCodeTheme = (savedProfile && savedProfile.code_theme) || readStored(CODE_THEME_STORAGE_KEY, 'monokai');
  applyBodyCodeTheme(initialCodeTheme);

  function persistProfile(profile){
    if(!profile) return;
    const merged = Object.assign({}, savedProfile || {}, profile);
    savedProfile = merged;
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(merged));
      if(merged.theme) localStorage.setItem(THEME_STORAGE_KEY, merged.theme);
      if(merged.code_theme) localStorage.setItem(CODE_THEME_STORAGE_KEY, merged.code_theme);
    } catch (err) {
      /* localStorage might be unavailable */
    }
  }

  function collectProfileFromForm(frm){
    if(!frm) return null;
    const result = {};
    const fields = ['fullName','username','email','role','bio'];
    for(const name of fields){
      if(frm.elements[name]){
        result[name] = frm.elements[name].value || '';
      }
    }
    if(frm.elements.remember){
      result.remember = !!frm.elements.remember.checked;
    }
    return result;
  }

  function showToast(msg, ok=true){
    if(!toast) return;
    toast.textContent = msg;
    toast.classList.remove('hidden');
    toast.style.borderColor = ok? 'rgba(78,238,234,0.12)' : 'rgba(255,90,90,0.12)';
    setTimeout(()=>toast.classList.add('hidden'), 3800);
  }

  function launchConfetti(){
    // existing lightweight confetti adapted for color and motion
    const cv = document.createElement('canvas');
    cv.style.position='fixed'; cv.style.left=0; cv.style.top=0; cv.style.pointerEvents='none'; cv.style.zIndex=999;
    cv.width = window.innerWidth; cv.height = window.innerHeight; document.body.appendChild(cv);
    const c = cv.getContext('2d');
    const colors = ['#4deeea','#8a6cff','#ffd86b','#6fffbf','#ff7ad1'];
    const pieces = [];
    for(let i=0;i<140;i++){
      pieces.push({x:window.innerWidth/2 + (Math.random()-0.5)*240, y:window.innerHeight/2 + (Math.random()-0.5)*140, vx:(Math.random()-0.5)*10, vy:-8 - Math.random()*8, r:4+Math.random()*8, c:colors[Math.floor(Math.random()*colors.length)], rot:Math.random()*360, vr:(Math.random()-0.5)*12});
    }
    let t0 = null;
    function step(ts){
      if(!t0) t0 = ts; const dt = Math.min((ts - t0)/1000,0.06); t0 = ts;
      c.clearRect(0,0,cv.width,cv.height);
      for(const p of pieces){
        p.vy += 18 * dt; p.x += p.vx; p.y += p.vy; p.rot += p.vr * dt;
        c.save(); c.translate(p.x,p.y); c.rotate(p.rot*Math.PI/180);
        c.fillStyle = p.c; c.fillRect(-p.r/2,-p.r/2,p.r,p.r*1.6);
        c.restore();
      }
      for(let i=pieces.length-1;i>=0;i--){ if(pieces[i].y>cv.height+60) pieces.splice(i,1); }
      if(pieces.length>0) requestAnimationFrame(step); else cv.remove();
    }
    requestAnimationFrame(step);
  }

  // button ripple
  if(btn){
    btn.addEventListener('click', (e)=>{
      const rect = btn.getBoundingClientRect();
      const r = Math.max(rect.width, rect.height);
      const ripple = document.createElement('span'); ripple.className='ripple';
      ripple.style.width = ripple.style.height = r*2 + 'px';
      ripple.style.left = (e.clientX - rect.left - r) + 'px';
      ripple.style.top = (e.clientY - rect.top - r) + 'px';
      btn.appendChild(ripple);
      requestAnimationFrame(()=>{ ripple.style.transform='scale(1)'; ripple.style.opacity='0'; });
      setTimeout(()=>ripple.remove(),700);
    });
  }

  if(form && btn){
    if(savedProfile){
      if(savedProfile.fullName && form.elements.fullName){ form.elements.fullName.value = savedProfile.fullName; }
      if(savedProfile.username && form.elements.username){ form.elements.username.value = savedProfile.username; }
      if(savedProfile.email && form.elements.email){ form.elements.email.value = savedProfile.email; }
      if(savedProfile.role && form.elements.role){ form.elements.role.value = savedProfile.role; }
      if(savedProfile.bio && form.elements.bio){ form.elements.bio.value = savedProfile.bio; }
      if(typeof savedProfile.remember === 'boolean' && form.elements.remember){ form.elements.remember.checked = savedProfile.remember; }
    }

    const debounce = (fn, delay)=>{
      let to = null;
      return function(...args){
        clearTimeout(to);
        to = setTimeout(()=>fn.apply(this,args), delay);
      };
    };

    const rememberDraft = debounce(()=>{
      const profileDraft = collectProfileFromForm(form);
      if(profileDraft && (profileDraft.fullName || profileDraft.username || profileDraft.email)){
        persistProfile(profileDraft);
      }
    }, 220);

    form.addEventListener('input', rememberDraft);
    form.addEventListener('change', rememberDraft);

    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      btn.disabled = true; btn.textContent = 'Sending...';

      const data = {};
      new FormData(form).forEach((v,k)=>data[k]=v);

      const profileSnapshot = {
        fullName: data.fullName || '',
        username: data.username || '',
        email: data.email || '',
        role: data.role || 'explorer',
        bio: data.bio || '',
        remember: form.elements.remember ? form.elements.remember.checked : false
      };
      const currentTheme = THEMES.find((theme)=>document.body.classList.contains(`theme-${theme}`)) || initialTheme;
      const currentCodeTheme = CODE_THEMES.find((theme)=>document.body.classList.contains(`code-theme-${theme}`)) || initialCodeTheme;
      profileSnapshot.theme = currentTheme;
      profileSnapshot.code_theme = currentCodeTheme;
      if(profileSnapshot.fullName || profileSnapshot.username || profileSnapshot.email){
        persistProfile(profileSnapshot);
      }

      try{
        const resp = await fetch(`${API_BASE}/api/register`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
        let payload = null;
        try {
          payload = await resp.json();
        } catch (parseErr) {
          payload = null;
        }

        if(resp.ok && payload && payload.success){
          showToast('Welcome aboard — id: '+payload.id,true);
          try{ launchConfetti(); }catch(e){/* ignore */}
          persistProfile(profileSnapshot);
          // persist simple token so the dashboard can allow profile edits
          try{
            const stored = JSON.parse(localStorage.getItem(PROFILE_KEY) || 'null') || {};
            stored.token = payload.id;
            localStorage.setItem(PROFILE_KEY, JSON.stringify(stored));
          }catch(e){/* ignore */}
          try { localStorage.setItem('futurereg-api-base', API_BASE); } catch (err) { /* ignore */ }
          setTimeout(()=>{
            const dashUrl = `${API_BASE}/dashboard`;
            window.location.href = dashUrl;
          }, 900);
        } else {
          const message = (payload && payload.error) ? payload.error : `Registration failed (${resp.status||'error'})`;
          showToast(message,false);
        }
      }catch(err){
        showToast(`Could not reach server at ${API_BASE} — open README to run backend`,false);
        console.error(err);
      } finally{ btn.disabled=false; btn.textContent='Register'; }
    });
  }

  if(loginForm){
    if(savedProfile){
      const loginUserField = loginForm.elements.loginUsername;
      if(loginUserField){ loginUserField.value = savedProfile.username || savedProfile.email || loginUserField.value; }
      if(typeof savedProfile.remember === 'boolean' && loginForm.elements.loginRemember){ loginForm.elements.loginRemember.checked = savedProfile.remember; }
    }

    loginForm.addEventListener('submit', (ev)=>{
      ev.preventDefault();
      const username = loginForm.elements.loginUsername ? loginForm.elements.loginUsername.value.trim() : '';
      if(!username){
        showToast('Enter your callsign to continue', false);
        return;
      }
      const remember = loginForm.elements.loginRemember ? !!loginForm.elements.loginRemember.checked : false;
      const updatedProfile = Object.assign({}, savedProfile || {}, { username, remember });
      persistProfile(updatedProfile);
      try { localStorage.setItem('futurereg-api-base', API_BASE); } catch (err) { /* ignore */ }
      showToast('Launching dashboard...', true);
      setTimeout(()=>{
        const dashUrl = `${API_BASE}/dashboard`;
        window.location.href = dashUrl;
      }, 400);
    });
  }

})();
