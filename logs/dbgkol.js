async () => {
  try {
    const m = await import('/assets/js/views/kol.js?v=' + Date.now());
    const root = document.createElement('div');
    root.className = 'view';
    m.render(root);
    return 'RENDER OK rows=' + root.querySelectorAll('tbody tr').length;
  } catch (e) {
    return 'ERR: ' + e.message + ' STACK: ' + String(e.stack || '').slice(0, 500);
  }
}
