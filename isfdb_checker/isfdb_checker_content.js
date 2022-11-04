/*global browser:false, fetch:false, location:false, sanitiseURL:false,
  SitePattern:false, testServerConnectivity:false, countLinkClasses:false,
  URL:false, Regexp:false */

/* Content script for ISFDB Checker web extension */

/* This started off as a copypaste of another extension I wrote, so there's
   likely a lot of unwanted code to be removed */

"use strict";

var options = {}; // Is it safe/preferable/avoidable to have this as a global?

function clog(txt) {
    console.log("isfdb_checker_content.js: " + txt);
}
function cwarn(txt) {
    console.warn("isfdb_checker_content.js: " + txt);
}
function cdir(obj) {
    console.log("isfdb_checker_content.js...");
    console.dir(obj);
}

/* Known false positives that shouldn't be highlighted */
const PATTERNS_TO_IGNORE = [
    /* I don't think Goodreads uses ISBNs or ASINs anywhere (except maybe in
       search results pages if you searched on them?), and has 10-digit IDs
       that look like ISBN-10s, so ignore everything on that site */
       new RegExp("www.goodreads.com")
];


function sendDownloadRequest(url) {
    /* NB: the options.subaction=resave doesn't currently have any effect,
       due to poor control of the saved filename across browsers (see comments
       in the download() function.  Maybe one day we can support it? */
    browser.runtime.sendMessage({action: "download", url: url,
                                 options: {subaction: "resave"}},
        function callback(resp) {
            clog("sendDownloadRequest.callback called");
            if (resp && resp.filename) {
                clog("Downloads as " + resp.filename);
            } else {
                cwarn("empty response?");
            }
        }
    );
}

function sendGenericMessage(req) {
    var retVal = false;
    browser.runtime.sendMessage(req,
        function callback(resp) {
            // clog("sendGenericMessage.callback called");
            if (resp && resp.success) {
                if (resp.message) {
                    clog("Successful request: " + resp.message);
                }
            retVal = resp.success;
            } else {
                // cwarn("Failed request: " + resp.message);
                cwarn("Failed request");
                cdir(resp);
            }
        }
    );
    return retVal;
}




function savePageViaExternalServer(server, extraHeaders) {
    /* Seems like documentElement.outerHTML omits the doctype -
       it's in document.doctype, perhaps we could pass it some other way.
       NB: that's an object, use the .name property
     */
    var content = document.documentElement.outerHTML;
    sendGenericMessage({action: "setIcon", status: "DOWNLOADING"});
    let headers = {
            "Content-Type": "text/html", // Q. Do we need this?
            "X-ISDFB-Checker": browser.runtime.getManifest().version
        };
    if (extraHeaders) {
        headers = Object.assign(headers, extraHeaders);
    }
    fetch(server + "/" + location.href, {
        method: "POST",
        mode: "cors", // Q: will we need this for a web-extension?
        headers: headers,
        body: content
    }).then(function parseResponse(resp) {
        return resp.json();
    }).then(function success(resp) {
        // clog("Fetch returned, response below...");
        // cdir(resp);
        sendGenericMessage({action: "setIcon", status: "DOWNLOADED"});
        return resp.savedAs;
    }).catch(function errorResponse(resp) {
        clog("Fetch failed, response/error below...");
        cdir(resp);
        sendGenericMessage({action: "setIcon", status: "ERROR"});
    });

}

function sendCheckRequestToServer(idToCheck, callback, server, extraHeaders) {
    // sendGenericMessage({action: "setIcon", status: "CHECKING"});
    let headers = {
            "Content-Type": "application/json",
            "X-ISDFB-Checker": browser.runtime.getManifest().version
        };
    if (extraHeaders) {
        headers = Object.assign(headers, extraHeaders);
    }
    fetch(server + "/check/" + idToCheck, {
        method: "GET",
        mode: "cors", // Q: will we need this for a web-extension?
        headers: headers //,
        // body: content
    }).then(function parseResponse(resp) {
        return resp.json();
    }).then(function success(resp) {
        clog("Fetch returned, response below...");
        cdir(resp);
        if (callback) {
            callback(resp);
        }

        // sendGenericMessage({action: "setIcon", status: "DOWNLOADED"});
        return resp.savedAs;
    }).catch(function errorResponse(resp) {
        clog("Fetch failed, response/error below...");
        cdir(resp);
        sendGenericMessage({action: "setIcon", status: "ERROR"});
    });

}

function sendBatchCheckRequestsToServer(idsToCheck, callback, server, extraHeaders) {
    // sendGenericMessage({action: "setIcon", status: "CHECKING"});
    let headers = {
            "Content-Type": "application/json",
            "X-ISDFB-Checker": browser.runtime.getManifest().version
        };
    if (extraHeaders) {
        headers = Object.assign(headers, extraHeaders);
    }
    fetch(server + "/batch_check/", {
        method: "POST",
        mode: "cors", // Q: will we need this for a web-extension?
        headers: headers,

        body: JSON.stringify(idsToCheck)
    }).then(function parseResponse(resp) {
        return resp.json();
    }).then(function success(resp) {
        // clog("Fetch returned, response below...");
        // cdir(resp);
        if (callback) {
            callback(resp);
        }

        // sendGenericMessage({action: "setIcon", status: "DOWNLOADED"});
        return resp.savedAs;
    }).catch(function errorResponse(resp) {
        clog("Fetch failed, response/error below...");
        cdir(resp);
        sendGenericMessage({action: "setIcon", status: "ERROR"});
    });

}



function isPageToBeDownloaded(url) {
    if (options.site_patterns) {
        return options.site_patterns.some( function checkSitePattern(sp) {
            return sp.doesDomainMatch(document.domain) &&
                (sp.doesUrlMatch(url) || sp.doesTitleMatch(document.title));
        });
    } else {
        cwarn("options.site_patterns does not exist?!?");
        return false;
    }
}



function isAmazonISBNSearch(urlArg) {
/** Given a URL, return an ISBN if this is an Amazon search for a particular
    ISBN, else null or some other falsey value.

    urlArg can either be a JavaScript URL object, or a string.
*/
    /* An example Amazon search URL that Locus uses
       http://www.amazon.com/gp/search?keywords=9781250176202&index=books&linkCode=qs&tag=locusmagazine

       e.g. as found on https://locusmag.com/2020/06/new-books-23-june-2020/

       Update: in 2021, they're using a different form:
       https://www.amazon.com/s?k=9780593085172&tag=locusmag06-20
       as seen at https://locusmag.com/2021/02/2020-locus-recommended-reading-list/
    */
    let url = urlArg;
    if (typeof urlArg == 'string') {
        url = new URL(urlArg);
    }
    if (url.hostname.search("amazon") < 0) {
        return null;
    }
    let val = null;
    if (url.pathname.startsWith("/gp/search")) {
        // Old style (prior to Jan 2021)
        val = url.searchParams.get("keywords"); // Returns null if not found
    }
    if (url.pathname === "/s") { // Exact match reqd given how terse it is
        // New style (as of Jan 2021)
        val = url.searchParams.get("k"); // Returns null if not found
    }
    if (!val) {
        return val;
    }
    // Very basic ISBN check (this should maybe be a standalone function?)
    // Note that this will
    const sanitisedVal = val.toUpperCase().replace( /[^0-9X]/g, "");
    if ((sanitisedVal.length != 10) && (sanitisedVal.length != 13)) {
        // Maybe it's an (ebook) ASIN?
        if (val.length == 10 && val[0] == 'B') {
            return val;
        }
    }
    return sanitisedVal;
}


function extractIdFromURL(urlArg) {
    /** Given a URL, return any embedded ISBN or ASIN, or null if no ID could be
        determined..
        (More accurately, return anything that looks like it might be one of
        those IDs) */
    // clog('urlArg is ' + urlArg); // Way too chatty
    if (!urlArg.startsWith("http")) {
        return null;
    }
    for (let i=0; i<PATTERNS_TO_IGNORE.length; i++) {
        if (urlArg.search( PATTERNS_TO_IGNORE[i] ) >= 0) {
            return null;
        }
    }

    const url = new URL(urlArg);
    const pathBits = url.pathname.split('/');
    for (let i=0; i<pathBits.length; i++) {
        let val = pathBits[i];
        if (val.endsWith(".html")) { // Penguin does this
            // If there are variants of this, making it more flexible using
            // RegExps
            val = val.substring(0, val.length - 5);
        }


        // clog("Checking " + pathBits[i]);
        if (val == "dp" && i < pathBits.length-1 &&
            pathBits[i+1].length == 10) {
            clog(pathBits[i+1] + " is an ASIN");
            return pathBits[i+1];
        }
        if (val == "gp" && i < pathBits.length-2 &&
            (pathBits[i+1] === "product") &&
            (pathBits[i+2].length == 10)) {
            /*
             * /gp/product/{ASIN} URLs are used on author pages e.g.
             * https://www.amazon.co.uk/Mercedes-Lackey/e/B000APZNR0/
             */
            clog(pathBits[i+2] + " is an ASIN (/gp/product/)");
            return pathBits[i+2];
        }
        if (val.search( /[\d \-]{13,}/ ) === 0) {
            console.log(val + " might be an ISBN-13");
            // Might be an ISBN-13
            const sanitised = val.replace( /[ \-]/g , '');
            if (sanitised.length === 13 && sanitised.search( /\d{13}/ === 0)) {
                clog(sanitised + " is an ISBN-13");
                return sanitised;
            } else {
                clog(val + " is not an ISBN-13 / sanitised form is '" + sanitised + "'");
            }
        }
        // Q: Can ISBN-10s have spaces or hyphens in?  I don't think I've
        //    seen any instances of that?
        if (val.search( /[\dX]{10,}/ === 0)) {
            // Might be an ISBN-10
            const sanitised = val.replace( /[ \-]/g , '');
            if (sanitised.length === 10 && sanitised.search( /[\dX]{10}/ ) === 0) {
                clog(sanitised + " is an ISBN-10");
                return sanitised;
            }
        }
    }

    // Special cases
    const amazonSearchISBN = isAmazonISBNSearch(url);
    if (amazonSearchISBN) {
        return amazonSearchISBN;
    }

    // clog("Returning null for " + urlArg);
    return null;
}


/** This function is (probably?) defunct now that we do highlights via an
    injected stylesheet and CSS class */
function _modifyLinkEl(linkEl, colour) {
    const backgroundStyling = colour;
    const borderStyling = "5px solid " + colour;
    linkEl.style.background = backgroundStyling;
    linkEl.querySelectorAll('img').forEach((imgEl) => {
        imgEl.style.border = borderStyling;
                                 });
    linkEl.querySelectorAll('span').forEach((el) => {
        el.style.background = backgroundStyling;
                                  });
    linkEl.querySelectorAll('div').forEach((el) => {
        el.style.background = backgroundStyling;
    });
}

function highlightLinkElAsUnknownToISFDB(linkEl,) {
    // _modifyLinkEl(linkEl, "pink");
    linkEl.classList.add("isfdb-checker-highlight-unknown");
    // Q: do we need to apply this to child img/span/divs?  Seems not...
}
function highlightLinkElAsKnownToFixer(linkEl,) {
    // _modifyLinkEl(linkEl, "purple");
    linkEl.classList.add("isfdb-checker-highlight-known-to-fixer");
}

function sendLinksToBackgroundScript() {
    let links = Array.from(document.querySelectorAll('a')); // NodeList doesn't support .map(), so convert to array

    /* Because the background script can't access the page DOM, send it everything
       it needs now.  Downside of this approach if that any links get added after
       page load, they won't be opened.  Example of this are GR yearly reading
       challenge pages e.g. https://www.goodreads.com/user_challenges/NNNNNNNN
       which only show the most recent 10 books, and have a "View More" button
       to show the rest */

    /*
    let linkClasses = links.map((el) => {
        let cssClasses = Array.from(el.classList);
        let parentClasses = [];
        if (cssClasses.length === 0) { // Or we could do this for all elements?
            parentClasses = Array.from(el.parentElement.classList);
        }
        return [cssClasses, el.href, parentClasses];
    });
    sendGenericMessage({action: "createContextMenuItems", linkClasses: linkClasses,
        pageUrl: document.location.href});
        */

    let modifiedLinkCount = 0;

    let id2LinkEls = {}; // There will be multiple links for the same ID
    let numUniqueIdsFound = 0; // More efficient than Object.keys(id2LinkEls).length

    links.forEach((linkEl) => {
        let url = linkEl.href;
        if (url) {
            const extractedId = extractIdFromURL(linkEl.href);
            if (extractedId) {
                modifiedLinkCount++;
                if (id2LinkEls[extractedId]) {
                    id2LinkEls[extractedId].push(linkEl);
                } else {
                    numUniqueIdsFound++;
                    id2LinkEls[extractedId] = [linkEl];
                }
                /*
                if (modifiedLinkCount > 3) {
                    // TEMP HACK TO AVOID OVERLOADING MYSQL
                        // No longer relevant
                    return;
                }
                // highlightLinkEl(linkEl);
                let callback = function(checkerResponse) {
                    checkerResponse.forEach((item) => {
                        if (item["id"] === extractedId) {
                            if (!item["known"]) {
                                highlightLinkEl(linkEl);
                            }
                        } else {
                            cwarn("Ignoring response item " + item["id"] +
                                  "; waiting on " + extractedId);
                        }
                    });
                };
                sendCheckRequestToServer(extractedId,
                                         callback,
                                         "http://127.0.0.1:5000");
                */
            }
        } else {
            // Don't do console.warn as this bloats the errors window in the
            // extension manager
            // cwarn("Skipping <a> element with no URL/href?!? ");
            // cwarn(linkEl);
        }
    });



    let callback2 = function(checkerResponse) {
        clog("Received batch reponse from checker");
        // cdir(checkerResponse);
        checkerResponse.forEach((item) => {
            if (!item["known"]) {
                let highlightFunction = highlightLinkElAsUnknownToISFDB;
                let status = "unknown to ISFDB";
                if (item["status"] !== undefined) {
                    highlightFunction = highlightLinkElAsKnownToFixer;
                    status += " but known to Fixer";
                }
                // id2LinkEls[item["id"]].forEach(highlightLinkEl);
                const unknownId = item["id"];
                console.log("ID " + unknownId + " is " + status);
                id2LinkEls[unknownId].forEach((el) => {
                        /*
                    clog(item["id"] + "> Highlighting el with URL " +
                         el.href);
                        */
                    // highlightLinkEl(el);
                    highlightFunction(el);
                });
            }
        });
    };

    clog("Found " + modifiedLinkCount + " links with IDs, total of " +
        numUniqueIdsFound + " unique IDs (out of " +
        links.length + " total links on the page)");


    if (modifiedLinkCount > 0) {
        sendBatchCheckRequestsToServer(Object.keys(id2LinkEls),
                                   callback2,
                                   "http://127.0.0.1:5000");
    }

}


function insertStyles(doc) {
    // https://stackoverflow.com/questions/11371550/change-hover-css-properties-with-javascript
    const cssText = `
/* Q: Do we need to explicitly do span/div children background as well? */
/* The opacity (esp. with the hover) is for the cases where the element is on top
   of something else, and setting the background hides it.  Maybe we could do
   something cleverer for those cases, but the opacity (reducing if you hover over
   it) should be OK for the time being */
/* The !important on the background are to (try to) ensure we win over any page
   styling */
.isfdb-checker-highlight-unknown { background: pink !important; opacity: 0.9; }
.isfdb-checker-highlight-unknown:hover { opacity: 0.5; }
.isfdb-checker-highlight-unknown img { border: 5px solid pink !important; opacity: 0.9; }
.isfdb-checker-highlight-unknown img:hover { opacity: 0.5; }
.isfdb-checker-highlight-known-to-fixer { background: purple !important; opacity: 0.9; }
.isfdb-checker-highlight-known-to-fixer:hover { opacity: 0.5; }
.isfdb-checker-highlight-known-to-fixer img { border: 5px solid purple !important; opacity: 0.9; }
.isfdb-checker-highlight-known-to-fixer img:hover { opacity: 0.5; }
`;
    let styleEl = doc.createElement("style");
    if (styleEl.styleSheet) {
        styleEl.styleSheet.cssText = cssText;
    } else {
        styleEl.appendChild(document.createTextNode(cssText));
    }

    doc.getElementsByTagName('head')[0].appendChild(styleEl);
}

function main(options) {
    insertStyles(document);
    sendLinksToBackgroundScript();
}


function convertOptsToOptions(opts) {
    /* Note:
       * "opts" is the config/settings data that's persisted in the key/value
         store
       * "options" is a derived JavaScript object, and is what should be
         used in other functions
       */
    var optionsErrors = [];
    if (opts.download_type) {
        if (opts.download_type === "download") {
            options.useDownloadsApi = true;
        } else {
            options.useDownloadsApi = false;
            if (opts.server) {
                // TODO: validate it
                options.server = opts.server;
                testServerConnectivity(options.server, function successCallback(msg) {
                    sendGenericMessage({action: "setIcon", status: "OK", title: msg});
                }, function errorCallback(msg) {
                    sendGenericMessage({action: "setIcon", status: "DEAD", title: msg});
                });

            } else {
                optionsErrors.push("Server mode enabled, but no server configured!");
            }
        }
    } else {
        optionsErrors.push("Download type not configured");
    }

    if (opts.site_patterns) {
        const obj = JSON.parse(opts.site_patterns);
        //cdir(obj);
        options.site_patterns = obj.map((sp) => new SitePattern(sp)) || [];
    }
    if (opts.site_redirects) {
        options.siteRedirects = JSON.parse(opts.site_redirects);
    } else {
        options.siteRedirects = {};
    }



    if (optionsErrors.length > 0) {
        sendGenericMessage({action: "setIcon", status: "ERROR"});
        // Multiple alert dialogs would be pretty annoying, but you still
        // need to fix all the issues, so live with them...
        optionsErrors.forEach( (e) => alert("OPTIONS ERROR: " + e));
        sendGenericMessage({action: "openOptionsPage"}); // Can't be done from content script
        return null;
    } else {
        return options;
    }
}


function mainWrapper(opts) {
    /* TODO - restore this sooner rather than later
    let options = convertOptsToOptions(opts);
    if (options) {
        main(options);
    } else {
        console.error("Options were not parsed correctly - aborting");
    }
    */
    main({});
}

var getting = browser.storage.local.get(null,
                                        // Chromium/Blink uses callbacks
                                        mainWrapper);
if (getting) {
    // Firefox uses Promises
    getting.then(mainWrapper, function() {
        alert("Unable to load preferences from local storage - ISFDB Checker disabled");
    });
}


