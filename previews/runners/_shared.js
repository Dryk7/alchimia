// Template scène pour comparer animations de course
window.RUNNER_SCENE = function(canvas, drawRunner){
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
    // Fond piste rouge avec lignes blanches
    ctx.fillStyle = '#e85040';
    ctx.fillRect(0, 0, W, H);
    // Couloirs (5)
    const top = H * .15;
    for(let lane = 0; lane < 5; lane++){
      if(lane % 2 === 1){
        ctx.fillStyle = '#c84030';
        ctx.fillRect(0, top + lane * 60 + 2, W, 58);
      }
    }
    ctx.fillStyle = '#fff';
    for(let lane = 0; lane <= 5; lane++){
      ctx.fillRect(0, top + lane * 60, W, 1.5);
    }
    // Texture
    ctx.fillStyle = 'rgba(0,0,0,.12)';
    const texT = -(t * 1.5);
    for(let i = 0; i < 30; i++){
      const x = ((texT + i * 23) % (W + 23) + (W + 23)) % (W + 23);
      const y = ((i * 47) % H);
      ctx.fillRect(x, y, 2, 2);
    }
    // 3 coureurs alignés horizontalement sur des couloirs différents (lane 0, 2, 4)
    const phase = t * .15;
    drawRunner(ctx, W * .25, top + .5 * 60, 1.2, phase + 0,    '#e85040', '#7a5838', '#f0d4b0');
    drawRunner(ctx, W * .50, top + 2.5 * 60, 1.4, phase + 0.5, '#4a9fd9', '#3a2818', '#a8804a');
    drawRunner(ctx, W * .75, top + 4.5 * 60, 1.6, phase + 1.0, '#ffd060', '#c0c0c0', '#e0c098');
    requestAnimationFrame(drawScene);
  }
  resize();
  setTimeout(resize, 500);
  requestAnimationFrame(drawScene);
};
