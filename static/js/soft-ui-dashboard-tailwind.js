var page = window.location.pathname.split("/").pop().split(".")[0];
var aux = window.location.pathname.split("/");
var to_build = (aux.includes('pages')?'../':'./');
var STATIC_URL = "/static/";
var root = window.location.pathname.split("/")
if (!aux.includes("pages")) {
  page = "dashboard";
}

loadStylesheet(STATIC_URL + "css/perfect-scrollbar.css");
loadJS(STATIC_URL + "js/perfect-scrollbar.js", true);

if (document.querySelector("nav [navbar-trigger]")) {
  loadJS(STATIC_URL + "js/navbar-collapse.js", true);
}

if (document.querySelector("[data-target='tooltip']")) {
  loadJS(STATIC_URL + "js/tooltips.js", true);
  loadStylesheet(STATIC_URL + "css/tooltips.css");
}

if (document.querySelector("[nav-pills]")) {
  loadJS(STATIC_URL + "js/nav-pills.js", true);
}

if (document.querySelector("[dropdown-trigger]")) {
  loadJS(STATIC_URL + "js/dropdown.js", true);

}

if (document.querySelector("[fixed-plugin]")) {
  loadJS(STATIC_URL + "js/fixed-plugin.js", true);
}

if (document.querySelector("[navbar-main]")) {
  loadJS(STATIC_URL + "js/sidenav-burger.js", true);
  loadJS(STATIC_URL + "js/navbar-sticky.js", true);
}

if (document.querySelector("canvas")) {
  loadJS(STATIC_URL + "js/chart-1.js", true);
  loadJS(STATIC_URL + "js/chart-2.js", true);
}

function loadJS(FILE_URL, async) {
  let dynamicScript = document.createElement("script");

  dynamicScript.setAttribute("src", FILE_URL);
  dynamicScript.setAttribute("type", "text/javascript");
  dynamicScript.setAttribute("async", async);

  document.head.appendChild(dynamicScript);
}

function loadStylesheet(FILE_URL) {
  let dynamicStylesheet = document.createElement("link");

  dynamicStylesheet.setAttribute("href", FILE_URL);
  dynamicStylesheet.setAttribute("type", "text/css");
  dynamicStylesheet.setAttribute("rel", "stylesheet");

  document.head.appendChild(dynamicStylesheet);
}
