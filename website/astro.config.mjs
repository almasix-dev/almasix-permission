// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import almasixTheme from '@almasix/starlight-theme';

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
			plugins: [
				almasixTheme({
					github: 'almasix-dev/almasix-permission',
					product: 'Permission',
					hubUrl: 'https://almasix.com',
				}),
			],
			head: [
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
