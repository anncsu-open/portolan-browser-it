// Options of Portolan Browser Italia, merged over the browser's own config.js
// through SB_CONFIG. Only what differs from the official browser is here.

// The organisation that runs the site. It appears in the footer and in the
// links below; change it here when the project moves to portolan-sdi.
export const HOSTING_ORGANISATION = "anncsu-open";
const REPOSITORY = `https://github.com/${HOSTING_ORGANISATION}/portolan-browser-it`;

export default {
  catalogUrl: null,
  catalogTitle: "Portolan Browser Italia",
  // Relative, so it resolves under the site's path prefix.
  catalogImage: "./logo.svg",
  // The Italian subset of the Portolan registry, written at build time.
  registryUrl: "./registry-it.json",
  allowExternalAccess: true,
  locale: "it",
  fallbackLocale: "en",
  supportedLocales: ["it", "en"],
  detectLocaleFromBrowser: false,
  historyMode: "hash",
  footerLinks: [
    { label: "legal", url: `${REPOSITORY}/blob/main/docs/note-legali.md` },
    { label: "privacy", url: `${REPOSITORY}/blob/main/docs/privacy.md` },
    { label: "source", url: REPOSITORY },
    { label: "official", url: "https://browser.portolan-sdi.org" },
  ],
};
