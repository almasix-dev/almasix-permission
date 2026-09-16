// @ts-check
import { readFileSync } from 'node:fs';

import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	site: 'https://permission.almasix.com',
	base: '/',
	devToolbar: { enabled: false },
	integrations: [
		starlight({
			title: 'Permission',
			description:
				'Roles and permissions for Almasix — HasRoles, teams, middleware, Prism directives, and smith commands.',
			logo: {
				light: './src/assets/almasix-banner-light.svg',
				dark: './src/assets/almasix-banner-dark.svg',
				alt: 'Almasix',
				replacesTitle: true,
			},
			favicon: '/favicon.svg',
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/almasix-dev/almasix-permission' },
			],
			editLink: {
				baseUrl: 'https://github.com/almasix-dev/almasix-permission/edit/main/website/',
			},
			customCss: ['./src/styles/custom.css'],
			components: {
				Header: './src/components/Header.astro',
				PageFrame: './src/components/PageFrame.astro',
				SiteTitle: './src/components/SiteTitle.astro',
				ThemeSelect: './src/components/ThemeSelect.astro',
			},
			expressiveCode: {
				themes: ['one-dark-pro'],
				useStarlightDarkModeSwitch: false,
				useStarlightUiThemeColors: false,
				// Must stay true on Astro 7 / Sätteri: inlining puts CSS in a
				// set:html attribute, and `pre > code` in that CSS closes the
				// <style> tag early — frames go transparent, copy chrome breaks.
				emitExternalStylesheet: true,
				styleOverrides: {
					borderRadius: '0.85rem',
					borderWidth: '1px',
					codeFontFamily: "'JetBrains Mono', ui-monospace, monospace",
					codeFontSize: '0.9rem',
					codeBackground: '#282c34',
					codeForeground: '#abb2bf',
					frames: {
						shadowColor: 'rgba(0, 0, 0, 0.4)',
						editorBackground: '#282c34',
						terminalBackground: '#282c34',
					},
				},
			},
			head: [
				{
					tag: 'link',
					attrs: { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
				},
				{
					tag: 'link',
					attrs: {
						rel: 'preconnect',
						href: 'https://fonts.gstatic.com',
						crossorigin: true,
					},
				},
				{
					tag: 'script',
					content: readFileSync('./src/scripts/sidebar-accordion.js', 'utf8'),
				},
				{
					tag: 'meta',
					attrs: { property: 'og:image', content: 'https://permission.almasix.com/og.png' },
				},
				{
					tag: 'meta',
					attrs: { property: 'og:image:width', content: '1200' },
				},
				{
					tag: 'meta',
					attrs: { property: 'og:image:height', content: '630' },
				},
				{
					tag: 'meta',
					attrs: { property: 'og:image:alt', content: 'Almasix Permission — Almasix' },
				},
				{
					tag: 'meta',
					attrs: { name: 'twitter:image', content: 'https://permission.almasix.com/og.png' },
				},
				{
					tag: 'meta',
					attrs: { name: 'theme-color', content: '#F1511B' },
				},
				{
					tag: 'script',
					attrs: { type: 'application/ld+json' },
					content: "{\"@context\": \"https://schema.org\", \"@graph\": [{\"@type\": \"WebSite\", \"@id\": \"https://permission.almasix.com/#website\", \"url\": \"https://permission.almasix.com/\", \"name\": \"Almasix Permission\", \"description\": \"Roles and permissions for Almasix \\u2014 HasRoles, teams, middleware, Prism directives, and smith commands.\", \"publisher\": {\"@id\": \"https://almasix.com/#organization\"}, \"inLanguage\": \"en\"}, {\"@type\": \"SoftwareApplication\", \"@id\": \"https://permission.almasix.com/#software\", \"name\": \"Almasix Permission\", \"applicationCategory\": \"DeveloperApplication\", \"url\": \"https://permission.almasix.com/\", \"isPartOf\": {\"@id\": \"https://almasix.com/#software\"}, \"publisher\": {\"@id\": \"https://almasix.com/#organization\"}}]}",
				},

			],
			sidebar: [
				{ label: 'Home', slug: 'index' },
				{
					label: 'Permission',
					items: [
						{ label: 'Installation', slug: 'installation' },
						{ label: 'Roles', slug: 'roles' },
						{ label: 'Permissions', slug: 'permissions' },
						{ label: 'Teams', slug: 'teams' },
						{ label: 'Middleware and Prism', slug: 'middleware-and-prism' },
						{ label: 'Commands', slug: 'commands' },
					],
				},
			],
		}),
	],
});
