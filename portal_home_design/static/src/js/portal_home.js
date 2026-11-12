/* Regroups the tiles that other modules already added to /my.
   It never edits those modules: it only moves the rendered cards into sections.
   Order matters: the first matching rule wins. Anything unmatched goes to "Other". */
(function () {
    "use strict";

    var GROUPS = [
        {title: "Time & Leave",         tone: "blue",   match: /attendance|leave/i},
        {title: "Pay & Finance",        tone: "green",  match: /payslip|loan|expense/i},
        {title: "Requests & Approvals", tone: "orange", match: /travel|approval|document|resign|asset/i},
        {title: "Growth",               tone: "purple", match: /apprais|survey/i},
        {title: "Account",              tone: "blue",   match: /profile/i},
    ];

    function cardKey(card) {
        var a = card.querySelector("a[href]");
        return ((a && a.getAttribute("href")) || "") + " " + (card.textContent || "");
    }

    function run() {
        var rows = document.querySelectorAll("#portal_custom_category");
        if (!rows.length || document.querySelector(".ivis_groups")) { return; }

        var cards = [], seen = {};
        Array.prototype.forEach.call(rows, function (row) {
            var found = row.querySelectorAll(".o_portal_index_card");
            var list = found.length ? found : row.children;
            Array.prototype.forEach.call(list, function (c) {
                var a = c.querySelector("a[href]");
                var href = a ? a.getAttribute("href") : null;
                if (href && seen[href]) { return; }     // skip duplicate tiles
                if (href) { seen[href] = true; }
                cards.push(c);
            });
        });
        if (!cards.length) { return; }

        var buckets = GROUPS.map(function (g) { return {def: g, cards: []}; });
        var other = {def: {title: "Other", tone: "blue"}, cards: []};

        cards.forEach(function (card) {
            var key = cardKey(card), target = other;
            for (var i = 0; i < GROUPS.length; i++) {
                if (GROUPS[i].match.test(key)) { target = buckets[i]; break; }
            }
            target.cards.push(card);
        });

        var wrap = document.createElement("div");
        wrap.className = "ivis_groups";
        buckets.concat([other]).forEach(function (b) {
            if (!b.cards.length) { return; }
            var sec = document.createElement("section");
            sec.className = "ivis_group ivis_" + b.def.tone;
            var h = document.createElement("h2");
            h.textContent = b.def.title;
            var grid = document.createElement("div");
            grid.className = "ivis_grid";
            b.cards.forEach(function (c) { c.classList.add("ivis_tile"); grid.appendChild(c); });
            sec.appendChild(h);
            sec.appendChild(grid);
            wrap.appendChild(sec);
        });

        rows[0].parentNode.insertBefore(wrap, rows[0]);
        Array.prototype.forEach.call(rows, function (r) { r.style.display = "none"; });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", run);
    } else {
        run();
    }
})();
