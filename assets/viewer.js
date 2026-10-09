(function () {
  "use strict";

  var bookId = new URLSearchParams(location.search).get("book");
  var pageFlip = null;
  var images = [];
  var pageCount = 0;
  var aspect = 0.75;
  var curPage = 0;
  var resizeTimer = null;
  var dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2.5));

  function q(id) { return document.getElementById(id); }
  function pad3(n) { return ("000" + n).slice(-3); }

  function buildImages(dir, pages) {
    var list = [];
    for (var i = 1; i <= pages; i++) list.push(dir + "page-" + pad3(i) + ".webp");
    return list;
  }

  function avail() {
    var st = q("stage");
    var W = st.clientWidth - 28;
    var H = st.clientHeight - 28;
    if (W < 220) W = 220;
    if (H < 220) H = 220;
    return { W: Math.round(W), H: Math.round(H) };
  }

  function setPageNo(idx) {
    if (!pageCount) return;
    var c = Math.max(1, Math.min(pageCount, idx + 1));
    q("pageno").textContent = c + " / " + pageCount;
    q("prev").disabled = c <= 1;
    q("next").disabled = c >= pageCount;
  }

  // 横屏时封面/封底是单页，库把它放在半幅、另半幅留白；平移到居中
  // 第 1 页在右半幅（左移 25%），最后一页在左半幅（右移 25%）
  function applyFitOffset() {
    if (!pageFlip) return;
    var fit = q("fit");
    if (!fit) return;
    var orient = (pageFlip.getOrientation && pageFlip.getOrientation()) || "landscape";
    var idx = pageFlip.getCurrentPageIndex ? pageFlip.getCurrentPageIndex() : 0;
    var offset = 0;
    if (orient === "landscape") {
      if (idx === 0) offset = -25;
      else if (idx === pageCount - 1) offset = 25;
    }
    fit.style.transform = offset ? "translateX(" + offset + "%)" : "translateX(0)";
  }

  // 画布按 devicePixelRatio 渲染，再整体缩放回 CSS 尺寸 —— 解决高清屏发虚
  function initFlip() {
    var a = avail();
    var fit = q("fit");
    var book = q("book");
    book.style.width = Math.round(a.W * dpr) + "px";
    book.style.height = Math.round(a.H * dpr) + "px";
    book.style.transform = "scale(" + (1 / dpr) + ")";
    book.style.transformOrigin = "top left";
    fit.style.width = a.W + "px";
    fit.style.height = a.H + "px";

    pageFlip = new St.PageFlip(book, {
      width: Math.round(aspect * 1000),
      height: 1000,
      size: "stretch",
      minWidth: Math.round(320 * dpr),
      maxWidth: Math.round(a.W * dpr),
      minHeight: Math.round(200 * dpr),
      maxHeight: Math.round(a.H * dpr),
      drawShadow: true,
      maxShadowOpacity: 0.4,
      flippingTime: 700,
      showCover: true,
      usePortrait: true,
      autoSize: false,
      mobileScrollSupport: true,
      swipeDistance: 20,
      showPageCorners: true
    });
    pageFlip.loadFromImages(images);
    pageFlip.on("flip", function (e) { curPage = e.data; setPageNo(e.data); applyFitOffset(); });
    if (curPage > 0) { try { pageFlip.turnToPage(curPage); } catch (err) {} }
    setPageNo(curPage);
    requestAnimationFrame(applyFitOffset);
  }

  // 注意：StPageFlip 的 destroy() 会一并移除父元素 #book，所以销毁后必须重建它
  function relayout() {
    if (!pageFlip) return;
    curPage = pageFlip.getCurrentPageIndex();
    try { pageFlip.destroy(); } catch (e) {}
    var fit = q("fit");
    var old = document.getElementById("book");
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var fresh = document.createElement("div");
    fresh.id = "book";
    fit.appendChild(fresh);
    initFlip();
  }

  function boot(book) {
    q("vTitle").textContent = book.title || "电子画册";
    document.title = book.title || "电子画册";
    pageCount = book.pages || 0;
    if (!pageCount) { q("loading").textContent = "此画册没有可用页面。"; return; }
    images = buildImages(book.dir, pageCount);

    var probe = new Image();
    probe.onload = function () {
      if (probe.naturalWidth && probe.naturalHeight) {
        aspect = probe.naturalWidth / probe.naturalHeight;
      }
      q("loading").style.display = "none";
      initFlip();
    };
    probe.onerror = function () {
      q("loading").textContent = "页面图片加载失败，请检查资源路径。";
    };
    probe.src = images[0];
  }

  function load() {
    if (!bookId) { q("loading").textContent = "缺少画册参数。"; return; }
    fetch("catalog.json?v=" + Date.now(), { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (cat) {
        var found = null;
        (cat.categories || []).forEach(function (c) {
          (c.books || []).forEach(function (b) { if (b.id === bookId) found = b; });
        });
        if (!found) { q("loading").textContent = "未找到该画册。"; return; }
        boot(found);
      })
      .catch(function (e) { q("loading").textContent = "加载失败：" + e.message; });
  }

  function scheduleRelayout(delay) {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(relayout, delay);
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();

    q("prev").addEventListener("click", function () { if (pageFlip) pageFlip.flipPrev(); });
    q("next").addEventListener("click", function () { if (pageFlip) pageFlip.flipNext(); });

    q("full").addEventListener("click", function () {
      var st = q("stage");
      var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
      if (!fsEl) {
        var fn = st.requestFullscreen || st.webkitRequestFullscreen || st.msRequestFullscreen;
        if (fn) fn.call(st);
      } else {
        var ex = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
        if (ex) ex.call(document);
      }
    });

    document.addEventListener("keydown", function (e) {
      if (!pageFlip) return;
      if (e.key === "ArrowLeft") pageFlip.flipPrev();
      if (e.key === "ArrowRight") pageFlip.flipNext();
    });

    window.addEventListener("resize", function () { scheduleRelayout(250); });
    window.addEventListener("orientationchange", function () { scheduleRelayout(350); });
    ["fullscreenchange", "webkitfullscreenchange"].forEach(function (ev) {
      document.addEventListener(ev, function () { scheduleRelayout(350); });
    });
  });
})();
