/*global browser:false, chrome:false, fetch:false */

/* Generic support functions and definitions that don't make any assumption
   about environment

   These functions were extracted from a similar file for a different extension, would
   probably make sense at some point to refactor to make them really "common" to both.
*/

const ICON_PATHS = {
    "OK":          "icons/green_32.png",
    "DEAD":        "icons/black_32.png",
    "IRRELEVANT":  "icons/grey_32.png",
    "DOWNLOADING": "icons/yellow_32.png",
    "DOWNLOADED":  "icons/green_32.png",
    "ERROR":       "icons/red_32.png"
};

function setup() {
    // https://developer.mozilla.org/en-US/Add-ons/WebExtensions/Chrome_incompatibilities
    if (typeof browser === "undefined") {
        if (typeof chrome !== "undefined") {
            browser = chrome;
        } else {
            console.error("Neither browser nor chrome object detected :-(");
        }
    }
}

setup();

