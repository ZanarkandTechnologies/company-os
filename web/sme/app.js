import {setupSiteShell} from "/shared/site-shell.js";
import {mountSystemRouter} from "/shared/system-router.js";

setupSiteShell();
mountSystemRouter(document.querySelector("[data-system-router]"));
