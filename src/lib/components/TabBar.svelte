<script lang="ts">
	import { page } from '$app/state';

	const TABS = [
		{ href: '/calendar', label: '캘린더', icon: 'cal' },
		{ href: '/', label: '홈', icon: 'home' },
		{ href: '/camera', label: '카메라', icon: 'cam' }
	];
	const active = (href: string) =>
		href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(href);
</script>

<nav aria-label="주요 메뉴">
	{#each TABS as t (t.href)}
		<a href={t.href} class:on={active(t.href)} aria-current={active(t.href) ? 'page' : undefined}>
			{#if t.icon === 'cal'}
				<svg viewBox="0 0 24 24"
					><rect x="3.5" y="5" width="17" height="15.5" rx="3.5" /><line
						x1="3.5"
						y1="9.8"
						x2="20.5"
						y2="9.8"
					/><line x1="8.3" y1="5" x2="8.3" y2="2.8" /><line
						x1="15.7"
						y1="5"
						x2="15.7"
						y2="2.8"
					/></svg
				>
			{:else if t.icon === 'home'}
				<svg viewBox="0 0 24 24"
					><path d="M4 10.5 12 3.8l8 6.7v8.2a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 18.7Z" /><path
						d="M9.5 21v-5.5a1.5 1.5 0 0 1 1.5-1.5h2a1.5 1.5 0 0 1 1.5 1.5V21"
					/></svg
				>
			{:else}
				<svg viewBox="0 0 24 24"
					><path
						d="M4 8.5A2.5 2.5 0 0 1 6.5 6h1.4l1.2-1.7A2 2 0 0 1 10.7 3.4h2.6a2 2 0 0 1 1.6.9L16.1 6h1.4A2.5 2.5 0 0 1 20 8.5v9A2.5 2.5 0 0 1 17.5 20h-11A2.5 2.5 0 0 1 4 17.5Z"
					/><circle cx="12" cy="13" r="3.4" /></svg
				>
			{/if}
			<span>{t.label}</span>
		</a>
	{/each}
</nav>

<style>
	nav {
		position: fixed;
		bottom: 0;
		left: 50%;
		transform: translateX(-50%);
		width: 100%;
		max-width: var(--maxw);
		height: calc(var(--tab-h) + env(safe-area-inset-bottom));
		padding-bottom: env(safe-area-inset-bottom);
		background: color-mix(in srgb, var(--surface) 92%, transparent);
		backdrop-filter: blur(16px);
		border-top: 1px solid var(--line);
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		z-index: 50;
	}
	a {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 2px;
		color: var(--text-4);
		font-size: 11px;
		font-weight: 600;
		transition: color 0.15s;
	}
	a.on {
		color: var(--text);
	}
	svg {
		width: 24px;
		height: 24px;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.8;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
</style>
