// Layout checks on the built site, run against a local preview:
//   node tests/visual/check_layout.mjs http://localhost:4173/portolan-browser-it/
// Uses the Playwright that the browser checkout installs as a dev dependency.
import { createRequire } from 'node:module';
const require = createRequire(new URL('../../.upstream/package.json', import.meta.url));
const { chromium } = require('@playwright/test');

const base = process.argv[2] ?? 'http://localhost:4173/portolan-browser-it/';
const catalog = `${base}#/external/pub-1e760dc850cb4a5aa5f8afb77713f8cd.r2.dev/catalog.json`;
const failures = [];
// CHROMIUM overrides the browser binary when Playwright's own is not installed.
const browser = await chromium.launch(
  process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {},
);
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

// The centre header as bootstrap-italia measures it (components/_headercenter.scss):
// band height, the part of it on screen, site name, logo, and whether it
// sticks to the top.
const header = () => {
  const site = document.querySelector('#stac-browser > header .site');
  const name = getComputedStyle(site.querySelector('.header-title span[role="banner"]'));
  const logo = site.querySelector('.header-title .logo').getBoundingClientRect();
  return {
    bandHeight: Math.round(site.getBoundingClientRect().height),
    bandOnScreen: Math.round(site.getBoundingClientRect().bottom),
    siteName: `${name.fontSize} ${name.fontWeight}`,
    logoHeight: Math.round(logo.height),
    logoInBand: logo.top >= 0 && logo.bottom <= site.getBoundingClientRect().bottom,
    headerPosition: getComputedStyle(document.querySelector('#stac-browser > header')).position,
  };
};

// The footer line that says who runs the site, in the page's language.
const disclaimer = () => page.evaluate(() => {
  const footer = document.querySelector('#stac-browser > footer');
  const line = [...footer.querySelectorAll('.custom-text')]
    .find((el) => el.getBoundingClientRect().height > 0);
  const links = footer.querySelector('.footer-links').getBoundingClientRect();
  return line && { text: line.textContent.trim(),
                   organisation: line.querySelector('a') && line.querySelector('a').href,
                   belowLinks: line.getBoundingClientRect().top >= links.bottom };
});

await page.goto(base);
await page.waitForSelector('#stac-browser > footer .footer-links');
// No slim bar: the blue header starts at the top of the page.
const top = await page.evaluate(() => ({
  slimBar: document.querySelectorAll('.it-slim').length,
  headerTop: Math.round(document.querySelector('#stac-browser > header').getBoundingClientRect().top),
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
}));
if (top.slimBar !== 0) failures.push('the slim bar is still on the page');
if (top.headerTop !== 0) failures.push(`the header starts ${top.headerTop}px from the top, expected 0`);
if (top.overflow > 0) failures.push(`page overflows horizontally by ${top.overflow}px`);

const italian = await disclaimer();
if (!italian || !italian.text.startsWith('Non è un sito istituzionale')) failures.push(`the footer does not say it is not an institutional site (${italian && italian.text})`);
else {
  if (!italian.organisation || !italian.organisation.startsWith('https://github.com/')) failures.push(`the footer line does not link the organisation (${italian.organisation})`);
  if (!italian.belowLinks) failures.push('the footer line is above the footer links');
}

// Bootstrap Italia 2.18.3 values: base font 16px, links underlined,
// buttons 600 with 12px 24px padding, inputs with only a bottom line.
const start = await page.evaluate(() => {
  const style = (sel) => { const el = document.querySelector(sel); return el && getComputedStyle(el); };
  const link = [...document.querySelectorAll('#stac-browser a')]
    .find((a) => a.textContent.includes('registro Portolan'));
  const button = style('.btn-primary');
  const input = style('input.form-control');
  return {
    bodyFont: getComputedStyle(document.body).fontSize,
    linkDecoration: link && getComputedStyle(link).textDecorationLine,
    buttonWeight: button && button.fontWeight,
    buttonPadding: button && `${button.paddingTop} ${button.paddingLeft}`,
    inputBorders: input && `${input.borderTopWidth} ${input.borderBottomWidth} ${input.borderRadius}`,
  };
});
if (start.bodyFont !== '16px') failures.push(`body font is ${start.bodyFont}, expected 16px`);
if (!String(start.linkDecoration).includes('underline')) failures.push(`content links are not underlined (${start.linkDecoration})`);
if (start.buttonWeight !== '600') failures.push(`buttons weigh ${start.buttonWeight}, expected 600`);
if (start.buttonPadding !== '12px 24px') failures.push(`buttons have padding ${start.buttonPadding}, expected 12px 24px`);
if (start.inputBorders !== '0px 1px 0px') failures.push(`inputs have borders/radius ${start.inputBorders}, expected 0px 1px 0px`);

await page.goto(catalog);
await page.waitForSelector('.catalog-card .card-title', { timeout: 30000 });
const cardFont = await page.evaluate(() =>
  getComputedStyle(document.querySelector('.catalog-card .card-title')).fontFamily);
if (!cardFont.includes('Titillium Web')) failures.push(`card titles use ${cardFont}`);

await page.waitForSelector('#stac-browser h2');
await page.waitForSelector('.badge');
// Headings 40px and 32px at weight 500, cards with 4px corners, bold badges,
// table cells with 8px padding.
const catalogPage = await page.evaluate(() => {
  const style = (sel) => { const el = document.querySelector(sel); return el && getComputedStyle(el); };
  return {
    h1: `${style('#stac-browser h1').fontSize} ${style('#stac-browser h1').fontWeight}`,
    h2: `${style('#stac-browser h2').fontSize} ${style('#stac-browser h2').fontWeight}`,
    cardRadius: style('.card').borderRadius,
    badgeWeight: style('.badge').fontWeight,
    cellPadding: style('table td') && style('table td').paddingTop,
    // The site title in the header is a link on every page but the start one.
    brandDecoration: getComputedStyle(document.querySelector('#stac-browser > header .site .title a')).textDecorationLine,
    footerBorder: style('#stac-browser > footer').borderTopWidth,
  };
});
Object.assign(catalogPage, await page.evaluate(`(${header})()`));
if (catalogPage.h1 !== '40px 500') failures.push(`h1 is ${catalogPage.h1}, expected 40px 500`);
if (catalogPage.h2 !== '32px 500') failures.push(`h2 is ${catalogPage.h2}, expected 32px 500`);
if (catalogPage.cardRadius !== '4px') failures.push(`cards have radius ${catalogPage.cardRadius}, expected 4px`);
if (catalogPage.badgeWeight !== '700') failures.push(`badges weigh ${catalogPage.badgeWeight}, expected 700`);
if (catalogPage.brandDecoration !== 'none') failures.push(`the header title is underlined (${catalogPage.brandDecoration})`);
if (catalogPage.footerBorder !== '0px') failures.push(`the footer has a ${catalogPage.footerBorder} top border`);
if (catalogPage.bandHeight !== 120) failures.push(`the header band is ${catalogPage.bandHeight}px high, expected 120`);
if (catalogPage.siteName !== '28px 600') failures.push(`the site name is ${catalogPage.siteName}, expected 28px 600`);
if (catalogPage.logoHeight !== 82) failures.push(`the logo is ${catalogPage.logoHeight}px high, expected 82`);
if (catalogPage.headerPosition !== 'sticky') failures.push(`the header is ${catalogPage.headerPosition}, expected sticky`);

// Scrolling down shrinks the band back to the browser's 72px, with a 24px
// name and a 40px logo, and keeps it on screen. The content keeps its place
// in the page: the header moves up instead of changing height.
const contentTop = () => page.evaluate(() =>
  Math.round(document.querySelector('#stac-browser h2').getBoundingClientRect().top + window.scrollY));
const contentBefore = await contentTop();
await page.evaluate(() => window.scrollTo(0, 400));
await page.waitForTimeout(600);
const scrolled = await page.evaluate(`({ ...(${header})(), scrollY: window.scrollY })`);
const contentAfter = await contentTop();
if (scrolled.bandOnScreen !== 72) failures.push(`scrolled down, ${scrolled.bandOnScreen}px of the header band are on screen, expected 72`);
if (scrolled.siteName !== '24px 600') failures.push(`scrolled down, the site name is ${scrolled.siteName}, expected 24px 600`);
if (scrolled.logoHeight !== 40) failures.push(`scrolled down, the logo is ${scrolled.logoHeight}px high, expected 40`);
if (!scrolled.logoInBand) failures.push('scrolled down, the logo sticks out of the band');
if (scrolled.scrollY !== 400) failures.push(`the page scrolled to ${scrolled.scrollY}, not 400`);
if (contentAfter !== contentBefore) failures.push(`the content moved from ${contentBefore}px to ${contentAfter}px in the page`);
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(600);
const back = await page.evaluate(`(${header})()`);
if (back.bandOnScreen !== 120 || back.siteName !== '28px 600') failures.push(`back at the top the band shows ${back.bandOnScreen}px with a ${back.siteName} name`);
if (catalogPage.cellPadding !== '8px') failures.push(`table cells have padding ${catalogPage.cellPadding}, expected 8px`);

// The same line in English once the visitor switches language.
await page.getByRole('button', { name: /Lingua/ }).click();
await page.getByRole('menuitem', { name: /English/ }).click();
await page.waitForFunction(() => document.documentElement.lang === 'en');
const english = await disclaimer();
if (!english || !english.text.startsWith('Not an institutional site')) failures.push(`the English footer line is ${english && english.text}`);

// On a phone: 20px name, 48px logo, nothing wider than the screen.
const phone = await browser.newPage({ viewport: { width: 375, height: 800 } });
await phone.goto(catalog);
await phone.waitForSelector('#stac-browser h2');
const mobile = await phone.evaluate(`({ ...(${header})(), overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth })`);
if (mobile.siteName !== '20px 600') failures.push(`on a phone the site name is ${mobile.siteName}, expected 20px 600`);
if (mobile.logoHeight !== 48) failures.push(`on a phone the logo is ${mobile.logoHeight}px high, expected 48`);
if (mobile.overflow > 0) failures.push(`on a phone the page overflows by ${mobile.overflow}px`);

await browser.close();
console.log(JSON.stringify({ ...top, italian, ...start, cardFont, ...catalogPage, scrolled, english, mobile }));
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('layout checks passed');
