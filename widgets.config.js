// Replaces the browser's widgets.config.js, which is empty upstream.
// The import climbs out of the browser checkout (.upstream/) to this
// repository's config, so the organisation name lives in one place.
import { HOSTING_ORGANISATION } from '../config.it.js';

const organisation = `[${HOSTING_ORGANISATION}](https://github.com/${HOSTING_ORGANISATION})`;

// A footer line that says who runs the site and that it is not an
// institutional one. CustomText has no translations, so there is one widget
// per language and the browser shows the one matching the current locale.
// Plain Markdown, so allowHTML stays off.
const footerLine = (text, shown) => ({
  id: 'CustomText',
  condition: ({ state }) => shown(state.locale),
  props: { text },
});

export default {
  'footer-start': [
    footerLine(
      `Non è un sito istituzionale · gestito da ${organisation}`,
      (locale) => locale === 'it',
    ),
    footerLine(
      `Not an institutional site · run by ${organisation}`,
      (locale) => locale !== 'it',
    ),
  ],
};
