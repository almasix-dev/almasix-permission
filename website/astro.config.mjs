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
				emitExternalStylesheet: false,
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
