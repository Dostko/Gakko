const chatButton = document.getElementById("chatButton");
const historyButton = document.getElementById("historyButton");
const fileButton = document.getElementById("fileButton");

const composerArea = document.querySelector(".composer-area");
const historyView = document.getElementById("historyView");
const historySearch = document.getElementById("historySearch");
const historyList = document.getElementById("historyList");
const historyDetail = document.getElementById("historyDetail");
const historyDeleteBefore = document.getElementById("historyDeleteBefore");
const historyDeleteBeforeButton = document.getElementById("historyDeleteBeforeButton");
const historyRetentionNote = document.getElementById("historyRetentionNote");

let bridge = null;
let currentView = "chat";
