// Template scène pour comparer designs personnages
window.CHARS_SCENE = function(canvas, drawChar){
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

  function drawScene(){
    t += 1;
    const W = canvas._W, H = canvas._H;
    if(!W || !H){ requestAnimationFrame(drawScene); return; }
    // Background piste avec lanes
    ctx.fillStyle = '#e85040';
    ctx.fillRect(0, 0, W, H);
    const top = H * .12;
    const laneH = 65;
    for(let lane = 0; lane < 5; lane++){
      if(lane % 2 === 1){
        ctx.fillStyle = '#c84030';
        ctx.fillRect(0, top + lane * laneH + 2, W, laneH - 4);
      }
    }
    ctx.fillStyle = '#fff';
    for(let lane = 0; lane <= 5; lane++){
      ctx.fillRect(0, top + lane * laneH, W, 1.5);
    }
    ctx.fillStyle = 'rgba(0,0,0,.12)';
    for(let i = 0; i < 40; i++){
      const x = ((i * 31 - t) % (W + 31) + (W + 31)) % (W + 31);
      const y = ((i * 47) % H);
      ctx.fillRect(x, y, 2, 2);
    }

    // Phase de course commune
    const phase = t * .15;
    // 5 perso à des positions / couleurs / tier différents
    const characters = [
      { x: W * .20, lane: 0, scale: 1.0, jersey: '#4a9fd9', skin: '#a8804a', hair: '#3a2818', tier: 0, accessory: {} },
      { x: W * .42, lane: 1, scale: 1.2, jersey: '#7ec46a', skin: '#f0d4b0', hair: '#7a5838', tier: 1, accessory: { cap:true } },
      { x: W * .58, lane: 2, scale: 1.35, jersey: '#e85040', skin: '#f0d4b0', hair: '#5a4028', tier: 2, accessory: {}, isHero: true },
      { x: W * .75, lane: 3, scale: 1.45, jersey: '#ffd060', skin: '#e0c098', hair: '#c0c0c0', tier: 3, accessory: { glasses:true } },
      { x: W * .92, lane: 4, scale: 1.55, jersey: '#e890b0', skin: '#88684a', hair: '#1a1010', tier: 4, accessory: { cap:true, glasses:true, bib:true } },
    ];
    characters.forEach((c, i) => {
      const y = top + (c.lane + 0.5) * laneH;
      drawChar(ctx, c.x, y, c.scale, phase + i * 0.6, c, t);
    });
    requestAnimationFrame(drawScene);
  }
  resize();
  setTimeout(resize, 500);
  requestAnimationFrame(drawScene);
};
