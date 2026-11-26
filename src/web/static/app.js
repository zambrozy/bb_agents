// Bidding table frontend: sample a deal, stream an auction (SSE),
// show the players' reasoning and the double-dummy analysis.

const SEATS = ["NORTH", "EAST", "SOUTH", "WEST"];
// Suit order of HandView.suits: S, H, D, C.
const SUITS = [
  { symbol: "♠", cls: "spades" },
  { symbol: "♥", cls: "hearts" },
  { symbol: "♦", cls: "diamonds" },
  { symbol: "♣", cls: "clubs" },
];
const STRAINS = ["NT", "S", "H", "D", "C"];
const STRAIN_SYMBOL = { S: "♠", H: "♥", D: "♦", C: "♣", NT: "NT" };
const STRAIN_CLASS = {
  S: "spades", H: "hearts", D: "diamonds", C: "clubs", NT: "",
};
const DD_SEATS = ["N", "S", "E", "W"];
const CALL_NAMES = { P: "Pass", X: "X", XX: "XX" };

let deal = null;      // DealView of the current deal
let players = {};     // seat -> {model, convention}
let source = null;    // EventSource of the running auction
let calls = [];       // accepted calls of the current auction
let thinking = null;  // seat on turn while the auction runs

const $ = (id) => document.getElementById(id);

// Element with an optional class and text: (tag, cls, text) -> Element.
function el(tag, cls = "", text = "") {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text) node.textContent = text;
  return node;
}

// Call such as "1S" with a coloured suit symbol: (str) -> Element.
function callNode(call) {
  const span = el("span", "call");
  const bid = /^([1-7])(NT|S|H|D|C)$/.exec(call);
  if (bid) {
    span.append(bid[1]);
    span.append(el("span", STRAIN_CLASS[bid[2]], STRAIN_SYMBOL[bid[2]]));
  } else {
    span.textContent = CALL_NAMES[call] ?? call;
  }
  return span;
}

// Status line under the controls: (str, bool) -> void.
function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
}

// Enable the buttons for the current state: () -> void.
function updateButtons() {
  const running = source !== null;
  $("new-deal").disabled = running;
  $("start").disabled = running || deal === null;
  $("stop").disabled = !running;
}

// Whether a seat is vulnerable: (seat, vulnerability) -> bool.
function isVulnerable(seat, vulnerability) {
  const ns = seat === "NORTH" || seat === "SOUTH";
  return vulnerability === "BOTH"
    || (vulnerability === "NS" && ns)
    || (vulnerability === "EW" && !ns);
}

// Seat due to call after `count` calls: (int) -> seat.
function seatAfter(count) {
  return SEATS[(SEATS.indexOf(deal.dealer) + count) % SEATS.length];
}

// --- Rendering ---------------------------------------------------

function renderHand(seat) {
  const box = $(`hand-${seat}`);
  box.replaceChildren();
  box.classList.toggle("active", seat === thinking);

  const head = el("div", "hand-head", seat);
  if (deal.dealer === seat) head.append(el("span", "badge", "dealer"));
  if (isVulnerable(seat, deal.vulnerability)) {
    head.append(el("span", "badge vul", "vul"));
  }
  const hand = deal.hands[seat];
  head.append(el("span", "hcp", `${hand.hcp} HCP`));
  box.append(head);

  const player = players[seat];
  if (player) {
    box.append(el(
      "div", "player", `${player.model} · ${player.convention}`,
    ));
  }
  hand.suits.forEach((ranks, i) => {
    const row = el("div", "suit-row");
    row.append(el("span", SUITS[i].cls, SUITS[i].symbol + " "));
    row.append(ranks || "—");
    box.append(row);
  });
  if (seat === thinking) box.append(el("div", "thinking", "thinking…"));
}

function renderHands() {
  SEATS.forEach(renderHand);
}

function renderAuction() {
  const body = $("auction").querySelector("tbody");
  body.replaceChildren();
  if (!deal) return;
  const cells = Array(SEATS.indexOf(deal.dealer)).fill(null);
  calls.forEach((call) => cells.push(call));
  if (thinking) cells.push("?");
  for (let i = 0; i < cells.length; i += SEATS.length) {
    const row = el("tr");
    cells.slice(i, i + SEATS.length).forEach((call) => {
      const cell = el("td");
      if (call === "?") {
        cell.className = "pending";
        cell.textContent = "…";
      } else if (call) {
        cell.append(callNode(call));
      }
      row.append(cell);
    });
    body.append(row);
  }
}

// DD table, optionally highlighting the contract cell:
// (done event | null) -> void.
function renderAnalysis(done = null) {
  const table = $("dd");
  table.replaceChildren();
  const head = el("tr");
  head.append(el("th"));
  DD_SEATS.forEach((seat) => head.append(el("th", "", seat)));
  table.append(head);
  STRAINS.forEach((strain) => {
    const row = el("tr");
    const label = el("th", STRAIN_CLASS[strain], STRAIN_SYMBOL[strain]);
    row.append(label);
    DD_SEATS.forEach((seat) => {
      const cell = el("td", "", String(deal.analysis.tricks[strain][seat]));
      if (done && done.strain === strain
          && done.declarer && done.declarer[0] === seat) {
        cell.classList.add("contract");
      }
      row.append(cell);
    });
    table.append(row);
  });
}

// Score with its sign, e.g. "+420", "−200", "0": (int) -> str.
function signed(score) {
  if (score > 0) return `+${score}`;
  if (score < 0) return `−${-score}`;
  return "0";
}

// One label/value row of the facts list: (str, Node | str,
// cls) -> void.
function addFact(box, label, value, cls = "") {
  box.append(el("dt", "", label));
  const dd = el("dd", cls);
  dd.append(value);
  box.append(dd);
}

// Contract column: the bid contract, its double-dummy result and
// score (after the auction), then par: (done event | null) -> void.
function renderResult(done) {
  const box = $("result");
  box.replaceChildren();
  if (done && !done.contract) {
    addFact(box, "Bid contract", "Passed out");
    addFact(box, "Score (NS)", signed(done.score_ns));
  } else if (done) {
    const [bid, ...rest] = done.contract.split(" ");
    const contract = el("span");
    contract.append(callNode(bid), ` ${rest.join(" ")}`);
    addFact(box, "Bid contract", contract);

    const play = el("span", "", `${done.dd_tricks} tricks, `
      + `needs ${done.needed} — `);
    if (done.result >= 0) {
      const extra = done.result > 0 ? ` +${done.result}` : "";
      play.append(el("span", "makes", `makes${extra}`));
    } else {
      play.append(el("span", "down", `down ${-done.result}`));
    }
    addFact(box, "Double dummy", play);
    addFact(box, "Score (NS)", signed(done.score_ns));
  } else {
    addFact(box, "Bid contract", "—", "muted");
  }

  box.append(el("hr"));
  addFact(box, "Par score", deal.analysis.par_score.join(" / "));
  deal.analysis.par_contracts.forEach((line) => {
    addFact(box, "Par contract", line, "muted");
  });
  if (done) {
    const cls = done.vs_par > 0 ? "makes" : done.vs_par < 0 ? "down" : "";
    addFact(box, "vs par (NS)", signed(done.vs_par), cls);
  }
}

function renderAll() {
  renderHands();
  renderAuction();
}

// --- Reasoning feed ----------------------------------------------

function addProposal(event) {
  const item = el("li");
  const head = el("div", "feed-head", `${event.seat}: `);
  head.append(callNode(event.call));
  if (event.try_nb > 0) {
    head.append(el("span", "feed-note", `  (retry ${event.try_nb})`));
  }
  item.append(head, el("p", "reasoning", event.reasoning));
  $("feed").append(item);
  item.scrollIntoView({ block: "nearest" });
}

// Mark the latest proposal: (cls, note) -> void.
function markLast(cls, note) {
  const item = $("feed").lastElementChild;
  if (!item) return;
  item.classList.add(cls);
  if (note) {
    item.querySelector(".feed-head").append(el("span", "feed-note", note));
  }
}

// --- Actions -----------------------------------------------------

async function loadPlayers() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) throw new Error((await response.json()).detail);
    players = (await response.json()).players;
  } catch (error) {
    setStatus(`Players config: ${error.message}`, true);
  }
}

async function newDeal(event) {
  event.preventDefault();
  const seed = $("seed").value;
  const body = {
    seed: seed === "" ? null : Number(seed),
    dealer: $("dealer").value,
    vulnerability: $("vulnerability").value,
  };
  try {
    const response = await fetch("/api/deals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    deal = await response.json();
  } catch (error) {
    setStatus(`Could not sample a deal: ${error.message}`, true);
    return;
  }
  calls = [];
  thinking = null;
  $("feed").replaceChildren();
  renderResult(null);
  renderAll();
  renderAnalysis();
  setStatus(`Deal ${deal.id} ready. ${deal.pbn}`);
  updateButtons();
}

// Close the stream and clear the turn marker: (str, bool) -> void.
function finish(message, isError = false) {
  if (source) source.close();
  source = null;
  thinking = null;
  renderAll();
  setStatus(message, isError);
  updateButtons();
}

function startBidding() {
  calls = [];
  thinking = deal.dealer;
  $("feed").replaceChildren();
  renderResult(null);
  renderAnalysis();
  renderAll();
  setStatus("Bidding…");

  source = new EventSource(`/api/deals/${deal.id}/bidding`);
  // Server events carry JSON data. The browser's own connection
  // "error" event shares a name with ours but has no data: skip it.
  const on = (name, handler) => source.addEventListener(
    name, (message) => {
      if (message.data !== undefined) handler(JSON.parse(message.data));
    },
  );

  on("proposal", addProposal);
  on("rejected", (event) => {
    markLast("rejected", `  rejected (try ${event.try_nb})`);
  });
  on("accepted", (event) => {
    if (event.forced) {
      markLast("rejected", "  rejected — forced pass");
    } else {
      markLast("accepted", "");
    }
    calls.push(event.call);
    thinking = seatAfter(calls.length);
    renderAll();
  });
  on("done", (event) => {
    renderResult(event);
    renderAnalysis(event);
    finish("Auction over.");
  });
  on("error", (event) => finish(`Error: ${event.message}`, true));
  // Connection problem (not the "error" event above): stop instead of
  // letting EventSource reconnect, which would restart the auction.
  source.onerror = () => {
    if (source) finish("Connection lost.", true);
  };
  updateButtons();
}

$("deal-form").addEventListener("submit", newDeal);
$("start").addEventListener("click", startBidding);
$("stop").addEventListener("click", () => finish("Stopped."));
loadPlayers();
