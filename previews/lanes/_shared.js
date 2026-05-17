// Template de scène partagé pour comparer les styles de couloirs
// Chaque preview override la fonction drawLanes(ctx, W, H, t, speed, pal)
window.SCENE_TEMPLATE = function(canvas, drawLanes){
  const ctx = canvas.getContext('2d');
  let t = 0;
  function resize(){
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    canvas._W = rect.width; canvas._H = rect.height;
  }
  window.addEventListener('resize', resize);
  setTimeout(resize, 50);

  const pal = { skyTop:'#7ec4ee', skyBot:'#c8e8f8', mountain:'#5870a8', tribune:'#a85820', tribuneLight:'#d88040', track:'#e85040', trackDark:'#7c2810' };
  const speed = 1.5;

  function drawScene(){
    t += 1;
    const W = canvas._W, H = canvas._H;
    if(!W || !H){ requestAnimationFrame(drawScene); return; }
    // Sky
    const sky = ctx.createLinearGradient(0, 0, 0, H * .55);
    sky.addColorStop(0, pal.skyTop); sky.addColorStop(1, pal.skyBot);
    ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H * .55);
    // Sun
    ctx.fillStyle = '#ffea88'; ctx.beginPath(); ctx.arc(W * .82, H * .12, 32, 0, Math.PI*2); ctx.fill();
    // Mountains
    ctx.fillStyle = pal.mountain;
    ctx.beginPath(); ctx.moveTo(0, H * .55);
    for(let i = -1; i <= W / 30 + 1; i++){
      const x = i * 30 + (-t * speed * 0.5) % 60;
      const baseH = H * .42;
      const peakH = baseH - 20 - Math.sin(i * 1.3) * 15 - Math.cos(i * .7) * 12;
      ctx.lineTo(x, peakH);
      ctx.lineTo(x + 15, baseH - 5 - Math.sin((i + 0.5) * 1.3) * 8);
    }
    ctx.lineTo(W, H * .55); ctx.lineTo(0, H * .55); ctx.fill();
    // Tribune
    ctx.fillStyle = pal.tribune; ctx.fillRect(0, H * .55 - 75, W, 75);
    ctx.fillStyle = pal.tribuneLight; ctx.fillRect(0, H * .55 - 70, W, 30);
    const crowdT = -(t * speed * 0.9);
    for(let i = 0; i < 60; i++){
      const x = ((crowdT + i * 14) % (W + 14) + (W + 14)) % (W + 14);
      const c = ['#e84030','#48a8e8','#48dc48','#ffd060','#ec90c0','#9080d0'][i % 6];
      ctx.fillStyle = c; ctx.fillRect(x, H * .55 - 60, 6, 8);
      ctx.fillRect(x, H * .55 - 38, 6, 6);
      ctx.fillStyle = '#f0d4b0'; ctx.fillRect(x, H * .55 - 68, 6, 6);
      ctx.fillRect(x, H * .55 - 44, 6, 5);
    }
    ctx.fillStyle = '#2c6090'; ctx.fillRect(0, H * .55 - 22, W, 18);
    // Track base
    ctx.fillStyle = pal.trackDark; ctx.fillRect(0, H * .55, W, 4);
    ctx.fillStyle = pal.track; ctx.fillRect(0, H * .55 + 4, W, H * .45 - 4);

    // === LANES (le focus de la comparaison) ===
    drawLanes(ctx, W, H, t, speed, pal);

    // Tartan dots
    ctx.fillStyle = 'rgba(0,0,0,.12)';
    const texT = -(t * speed * 1.2);
    for(let i = 0; i < 50; i++){
      const x = ((texT + i * 23) % (W + 23) + (W + 23)) % (W + 23);
      const y = H * .55 + ((i * 17) % (H * .42)) + 8;
      ctx.fillRect(x, y, 2, 2);
    }
    // Ombre tribune
    const grad = ctx.createLinearGradient(0, H * .55, 0, H * .55 + 20);
    grad.addColorStop(0, 'rgba(0,0,0,.25)'); grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad; ctx.fillRect(0, H * .55, W, 20);

    // Hero (red, lane 2)
    drawRunner(ctx, W * .35, H * (.60 + .12), 1.0, t * .25, '#e85040', '#7a5838', '#f0d4b0');
    // NPCs sur 4 couloirs différents
    const npcOffsets = [[W * .60, .03, .55, '#4a9fd9', '#3a2818'], [W * .45, .18, .65, '#7ec46a', '#8a6848'], [W * .70, .31, .80, '#ffd060', '#c0c0c0'], [W * .55, .50, .85, '#e890b0', '#dcd0c0']];
    npcOffsets.forEach(([x, lane, scale, jers, hair]) => {
      const y = H * (.60 + lane * .24);
      drawRunner(ctx, x, y, scale, t * .2, jers, hair, '#f0d4b0');
    });

    requestAnimationFrame(drawScene);
  }

  function drawRunner(ctx, x, y, scale, phase, jersey, hair, skin){
    const s = scale;
    ctx.fillStyle = 'rgba(0,0,0,.35)';
    ctx.beginPath(); ctx.ellipse(x, y + 28 * s, 18 * s, 4 * s, 0, 0, Math.PI*2); ctx.fill();
    const swing = Math.sin(phase);
    const legL = swing * 18 * s, legR = -swing * 18 * s;
    const armL = -swing * 22 * s, armR = swing * 22 * s;
    ctx.strokeStyle = skin; ctx.lineWidth = 7 * s; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(x - 4 * s, y + 5 * s); ctx.lineTo(x - 4 * s, y + 22 * s + legL); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 4 * s, y + 5 * s); ctx.lineTo(x + 4 * s, y + 22 * s + legR); ctx.stroke();
    ctx.fillStyle = jersey;
    ctx.beginPath(); ctx.ellipse(x - 4 * s, y + 25 * s + legL, 7 * s, 4 * s, 0, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(x + 4 * s, y + 25 * s + legR, 7 * s, 4 * s, 0, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.fillRect(x - 11 * s, y - 2 * s, 22 * s, 9 * s);
    ctx.fillStyle = jersey;
    const r = 6 * s;
    ctx.beginPath();
    ctx.moveTo(x - 13 * s + r, y - 22 * s); ctx.lineTo(x + 13 * s - r, y - 22 * s);
    ctx.quadraticCurveTo(x + 13 * s, y - 22 * s, x + 13 * s, y - 22 * s + r);
    ctx.lineTo(x + 13 * s, y); ctx.quadraticCurveTo(x + 13 * s, y, x + 13 * s - r, y);
    ctx.lineTo(x - 13 * s + r, y); ctx.quadraticCurveTo(x - 13 * s, y, x - 13 * s, y - r);
    ctx.lineTo(x - 13 * s, y - 22 * s + r); ctx.quadraticCurveTo(x - 13 * s, y - 22 * s, x - 13 * s + r, y - 22 * s);
    ctx.fill();
    ctx.fillStyle = '#ffd060'; ctx.fillRect(x - 13 * s, y - 22 * s, 26 * s, 4 * s);
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x, y - 11 * s, 5 * s, 0, Math.PI*2); ctx.fill();
    ctx.strokeStyle = skin; ctx.lineWidth = 6 * s;
    ctx.beginPath(); ctx.moveTo(x - 13 * s, y - 14 * s); ctx.lineTo(x - 22 * s, y - 2 * s + armL); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 13 * s, y - 14 * s); ctx.lineTo(x + 22 * s, y - 2 * s + armR); ctx.stroke();
    ctx.fillStyle = skin; ctx.beginPath(); ctx.arc(x, y - 34 * s, 14 * s, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = hair;
    ctx.beginPath(); ctx.arc(x, y - 38 * s, 14 * s, Math.PI, 0);
    ctx.lineTo(x + 12 * s, y - 32 * s); ctx.lineTo(x - 12 * s, y - 32 * s); ctx.fill();
    ctx.fillStyle = '#1a1010';
    ctx.beginPath(); ctx.arc(x + 2 * s, y - 33 * s, 1.8 * s, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(x + 9 * s, y - 33 * s, 1.8 * s, 0, Math.PI*2); ctx.fill();
  }

  resize();
  setTimeout(resize, 500);
  requestAnimationFrame(drawScene);
};
