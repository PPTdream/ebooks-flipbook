(function () {
  "use strict";

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function viewerUrl(book) {
    return "viewer.html?book=" + encodeURIComponent(book.id);
  }

  function load() {
    fetch("catalog.json?v=" + Date.now(), { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("catalog " + r.status);
        return r.json();
      })
      .then(render)
      .catch(function (e) {
        document.getElementById("shelves").appendChild(
          el("div", "empty", "画册索引加载失败：" + esc(e.message))
        );
      });
  }

  function render(cat) {
    var siteEl = document.getElementById("siteTitle");
    var subEl = document.getElementById("siteSub");
    if (cat.site) {
      if (cat.site.title) { siteEl.textContent = cat.site.title; document.title = cat.site.title; }
      if (cat.site.subtitle) subEl.textContent = cat.site.subtitle;
    }
    if (cat.updated) document.getElementById("updated").textContent = "更新 " + cat.updated;
    document.getElementById("year").textContent = (cat.updated || "").slice(0, 4) || new Date().getFullYear();

    var cats = cat.categories || [];
    var chipsBox = document.getElementById("cats");
    var shelves = document.getElementById("shelves");
    chipsBox.innerHTML = "";
    shelves.innerHTML = "";

    var total = 0;
    cats.forEach(function (c) { total += (c.books || []).length; });

    if (total === 0) {
      shelves.appendChild(el("div", "empty", "还没有画册。把 PDF 放进 <code>_source/&lt;分类&gt;/</code>，运行构建脚本即可。"));
      return;
    }

    function renderShelves(activeId) {
      shelves.innerHTML = "";
      cats.forEach(function (c) {
        if (activeId !== "all" && c.id !== activeId) return;
        if (!c.books || !c.books.length) return;
        var st = el("div", "shelf-title", esc(c.name) + " · " + c.books.length + " 本");
        shelves.appendChild(st);
        var grid = el("div", "grid");
        c.books.forEach(function (b) {
          var a = el("a", "book");
          a.href = viewerUrl(b);
          a.innerHTML =
            '<div class="cover"><span class="spine"></span>' +
            '<img loading="lazy" src="' + esc(b.cover) + '" alt="' + esc(b.title) + '"></div>' +
            '<div class="meta"><div class="t">' + esc(b.title) + "</div>" +
            '<div class="p">' + (b.pages || 0) + " 页</div></div>";
          grid.appendChild(a);
        });
        shelves.appendChild(grid);
      });
    }

    function makeChip(label, id) {
      var c = el("button", "chip", esc(label));
      c.addEventListener("click", function () {
        [].forEach.call(chipsBox.children, function (x) { x.classList.remove("on"); });
        c.classList.add("on");
        renderShelves(id);
      });
      return c;
    }

    var allChip = makeChip("全部 (" + total + ")", "all");
    allChip.classList.add("on");
    chipsBox.appendChild(allChip);
    cats.forEach(function (c) {
      if (!c.books || !c.books.length) return;
      chipsBox.appendChild(makeChip(c.name + " (" + c.books.length + ")", c.id));
    });

    renderShelves("all");
  }

  document.addEventListener("DOMContentLoaded", load);
})();
