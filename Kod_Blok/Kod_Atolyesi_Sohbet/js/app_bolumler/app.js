const chatButton = document.getElementById("chatButton");
const historyButton = document.getElementById("historyButton");
const fileButton = document.getElementById("fileButton");
const recordsButton = document.getElementById("recordsButton");

const composerArea = document.querySelector(".composer-area");
const recordsView = document.getElementById("recordsView");
const recordsSearch = document.getElementById("recordsSearch");
const recordsList = document.getElementById("recordsList");
const recordsDetail = document.getElementById("recordsDetail");
const recordsRefreshButton = document.getElementById("recordsRefreshButton");
const historyView = document.getElementById("historyView");
const historySearch = document.getElementById("historySearch");
const historyList = document.getElementById("historyList");
const historyDetail = document.getElementById("historyDetail");
const historyDeleteBefore = document.getElementById("historyDeleteBefore");
const historyDeleteBeforeButton = document.getElementById("historyDeleteBeforeButton");
const historyRetentionNote = document.getElementById("historyRetentionNote");

let bridge = null;
let recordsBridge = null;
let currentView = "chat";
