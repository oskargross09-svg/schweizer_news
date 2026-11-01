// Deterministic timeline: render(t) sets every element for time t (seconds).
const easeOut = x => 1 - Math.pow(1 - x, 4);           // ≈ cubic-bezier(.22,1,.36,1)
const easeInOut = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const clamp = x => Math.max(0, Math.min(1, x));
const scenes = [...document.querySelectorAll('.scene')];
const wipe = document.querySelector('.sn-wipe-x');
const WIPE = 0.4;

function render(t) {
  let idx = TL.findIndex(s => t >= s.start && t < s.start + s.dur);
  if (idx < 0) idx = TL.length - 1;
  scenes.forEach((el, i) => el.style.visibility = i === idx ? 'visible' : 'hidden');

  // red wipe across each cut (none before the intro)
  let wx = -100;
  for (let i = 1; i < TL.length; i++) {
    const b = TL[i].start;
    if (Math.abs(t - b) < WIPE / 2) wx = -100 + 200 * easeInOut(clamp((t - b + WIPE / 2) / WIPE));
  }
  wipe.style.transform = `translateX(${wx}%)`;

  const s = TL[idx], el = scenes[idx], lt = t - s.start;
  el.querySelectorAll('.anim').forEach(a => {
    const at = parseFloat(a.dataset.at), k = a.dataset.kind || 'in';
    if (k === 'drop') { const p = easeOut(clamp((lt - at) / 0.5)); a.style.transform = `translateY(${(p - 1) * 100}%)`; return; }
    if (k === 'bar' || k === 'rule') { const p = easeOut(clamp((lt - at) / 0.4)); a.style.transform = `scaleX(${p})`; return; }
    const p = easeOut(clamp((lt - at) / 0.3));
    a.style.opacity = p; a.style.transform = `translateY(${(1 - p) * 24}px)`;
  });
  el.querySelectorAll('.cell').forEach(c => {
    const at = 0.35 + (parseInt(c.dataset.row) / 23) * 0.4;
    c.style.opacity = easeOut(clamp((lt - at) / 0.15));
  });
  const mark = el.querySelector('.mark');
  if (mark) {
    const p = easeOut(clamp((lt - 0.85) / 0.3));
    mark.style.opacity = p > 0 ? 1 : 0;
    mark.style.clipPath = `inset(0 ${(1 - p) * 100}% 0 0)`;
  }
  el.querySelectorAll('.count').forEach(c => {
    const p = easeOut(clamp((lt - 0.15) / 0.5));
    c.textContent = Math.round(p * parseFloat(c.dataset.to)).toLocaleString('de-CH');
  });
}
window.render = render;
render(0);
