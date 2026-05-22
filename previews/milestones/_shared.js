// Shared rendering for milestone previews
// Renders: sky, tribune, athletics track, scrolling hero, three milestones (100m, 500m, 1 KM)
// Caller provides: drawKm(ctx, x, groundY, km, t)   for big km signs
//                  drawHm(ctx, x, groundY, meters, t)   for 100m / 500m markers

function MILESTONES_SCENE(canvas, drawKm, drawHm){
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const groundY = H * 0.78;       // surface de la piste
  const skyTop = H * 0.40;
  const tribuneTop = H * 0.42;

  // Markers — défilent en boucle de droite vers gauche
  // distance en mètres depuis le héros (positive = devant)
  const markers = [
    { type: 'hm', m: 100, dist: 80 },
    { type: 'hm', m: 500, dist: 280 },
    { type: 'km', km: 1, dist: 520 },
    { type: 'hm', m: 100, dist: 760 },
    { type: 'hm', m: 500, dist: 960 },
    { type: 'km', km: 2, dist: 1200 },
  ];
  const totalLen = 1400;

  let t = 0;
  function frame(){
    t += 1/60;

    // -- SKY gradient
    const sky = ctx.createLinearGradient(0, 0, 0, skyTop);
    sky.addColorStop(0, '#1c2030');
    sky.addColorStop(.5, '#2b3050');
    sky.addColorStop(1, '#3d3a4a');
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, W, skyTop);

    // -- Lointain (silhouette stade)
    ctx.fillStyle = '#1a1820';
    ctx.fillRect(0, skyTop - 18, W, 18);
    for(let i=0;i<8;i++){
      const sx = (i * 80 + (t*8) % 80) - 40;
      ctx.fillRect(sx, skyTop - 28, 24, 10);
    }

    // -- Tribune
    const tri = ctx.createLinearGradient(0, tribuneTop, 0, groundY - 8);
    tri.addColorStop(0, '#2a2a38');
    tri.addColorStop(1, '#1a1a25');
    ctx.fillStyle = tri;
    ctx.fillRect(0, tribuneTop, W, groundY - tribuneTop - 8);
    // Marches
    ctx.fillStyle = 'rgba(0,0,0,.25)';
    for(let i=0;i<5;i++){
      ctx.fillRect(0, tribuneTop + i * 8, W, 1);
    }

    // -- Mur de séparation
    ctx.fillStyle = '#0a0a10';
    ctx.fillRect(0, groundY - 8, W, 4);
    ctx.fillStyle = '#3a3a4a';
    ctx.fillRect(0, groundY - 4, W, 4);

    // -- Piste rouge
    const track = ctx.createLinearGradient(0, groundY, 0, H);
    track.addColorStop(0, '#c84030');
    track.addColorStop(1, '#a02818');
    ctx.fillStyle = track;
    ctx.fillRect(0, groundY, W, H - groundY);

    // Lignes de couloirs (perspective simple)
    ctx.strokeStyle = 'rgba(255,255,255,.5)';
    ctx.lineWidth = 1.5;
    for(let i=1;i<4;i++){
      const ly = groundY + (H - groundY) * (i / 4);
      ctx.beginPath();
      ctx.moveTo(0, ly);
      ctx.lineTo(W, ly);
      ctx.stroke();
    }

    // -- Scroll défilement
    const scrollSpeed = 60; // pixels/sec
    const offset = (t * scrollSpeed) % totalLen;

    // Texture piste (lignes de défilement)
    ctx.strokeStyle = 'rgba(255,255,255,.15)';
    ctx.lineWidth = 2;
    for(let i=0;i<8;i++){
      const dx = ((i * 140) - offset * 1.5) % (W + 200) - 100;
      ctx.beginPath();
      ctx.moveTo(dx, groundY + 4);
      ctx.lineTo(dx - 20, groundY + (H - groundY));
      ctx.stroke();
    }

    // -- Markers défilent
    markers.forEach(mk => {
      const x = W * 0.4 + mk.dist - offset;
      // wrap
      const xw = ((x % totalLen) + totalLen) % totalLen;
      const finalX = xw > W + 100 ? xw - totalLen : xw;
      if(finalX < -80 || finalX > W + 80) return;
      if(mk.type === 'km'){
        drawKm(ctx, finalX, groundY, mk.km, t);
      } else {
        drawHm(ctx, finalX, groundY, mk.m, t);
      }
    });

    // -- Hero au centre (pixel-style simple)
    drawHero(ctx, W * 0.4, groundY, t);

    requestAnimationFrame(frame);
  }

  function drawHero(ctx, x, y, t){
    const phase = t * 9;
    const swing = Math.sin(phase);
    const hop = Math.abs(Math.sin(phase * 2)) * 4;
    const by = y - 30 - hop;
    // Ombre
    ctx.fillStyle = 'rgba(0,0,0,.4)';
    ctx.beginPath(); ctx.ellipse(x, y + 2, 14, 3.5, 0, 0, Math.PI*2); ctx.fill();
    // Jambes
    ctx.strokeStyle = '#f4c8a8'; ctx.lineWidth = 5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(x - 3, by + 5); ctx.lineTo(x - 3, by + 18 + swing * 12); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 3, by + 5); ctx.lineTo(x + 3, by + 18 - swing * 12); ctx.stroke();
    // Chaussures
    ctx.fillStyle = '#c84030';
    ctx.beginPath(); ctx.ellipse(x - 3, by + 19 + swing * 12, 5, 3, 0, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(x + 3, by + 19 - swing * 12, 5, 3, 0, 0, Math.PI*2); ctx.fill();
    // Short
    ctx.fillStyle = '#fff';
    ctx.fillRect(x - 9, by - 1, 18, 8);
    // Corps
    ctx.fillStyle = '#c84030';
    ctx.fillRect(x - 10, by - 18, 20, 18);
    // Bandeau
    ctx.fillStyle = '#ffd060';
    ctx.fillRect(x - 10, by - 18, 20, 3);
    // Bras
    ctx.strokeStyle = '#f4c8a8'; ctx.lineWidth = 4.5;
    ctx.beginPath(); ctx.moveTo(x - 10, by - 11); ctx.lineTo(x - 17, by - 2 - swing * 6); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 10, by - 11); ctx.lineTo(x + 17, by - 2 + swing * 6); ctx.stroke();
    // Tête
    ctx.fillStyle = '#f4c8a8';
    ctx.beginPath(); ctx.arc(x, by - 28, 12, 0, Math.PI*2); ctx.fill();
    // Cheveux
    ctx.fillStyle = '#3a2818';
    ctx.beginPath();
    ctx.arc(x, by - 31, 12, Math.PI, 0);
    ctx.lineTo(x + 11, by - 26); ctx.lineTo(x - 11, by - 26); ctx.fill();
    // Yeux
    ctx.fillStyle = '#1a1010';
    ctx.beginPath(); ctx.arc(x - 3.5, by - 27, 1.8, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(x + 3.5, by - 27, 1.8, 0, Math.PI*2); ctx.fill();
    // Sourire
    ctx.strokeStyle = '#3a2818'; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(x, by - 23, 2.5, .2, Math.PI - .2); ctx.stroke();
  }

  frame();
}
