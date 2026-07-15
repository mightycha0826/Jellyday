<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { S, init } from '$lib/state.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import MedicationForm from '$lib/components/MedicationForm.svelte';
	import AddChooser from '$lib/components/AddChooser.svelte';

	let { children } = $props();

	$effect(() => {
		void init();
	});

	// 서비스 워커 등록 (프로덕션 빌드에서만 동작)
	$effect(() => {
		if (import.meta.env.PROD && 'serviceWorker' in navigator) {
			navigator.serviceWorker.register('/service-worker.js', { type: 'module' }).catch(() => {});
		}
	});

	// PWA 설치 프롬프트 캡처
	$effect(() => {
		if (matchMedia('(display-mode: standalone)').matches) S.installed = true;
		const onPrompt = (e: Event) => {
			e.preventDefault();
			S.installEvt = e;
		};
		const onInstalled = () => {
			S.installEvt = null;
			S.installed = true;
		};
		addEventListener('beforeinstallprompt', onPrompt);
		addEventListener('appinstalled', onInstalled);
		return () => {
			removeEventListener('beforeinstallprompt', onPrompt);
			removeEventListener('appinstalled', onInstalled);
		};
	});

	// 카메라 화면은 풀스크린 (탭바 숨김)
	const bare = $derived(page.url.pathname.startsWith('/camera'));
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if !S.booted}
	<div class="boot"><div class="spinner" aria-label="불러오는 중"></div></div>
{:else}
	{@render children()}
	{#if !bare}
		<TabBar />
	{/if}
	<AddChooser />
	<MedicationForm />
{/if}

<!-- 토스트 -->
<div class="toasts" aria-live="polite">
	{#each S.toasts as t (t.id)}
		<div class="toast">{t.msg}</div>
	{/each}
</div>

<style>
	.boot {
		min-height: 100dvh;
		display: grid;
		place-items: center;
	}
	.toasts {
		position: fixed;
		bottom: calc(var(--tab-h) + env(safe-area-inset-bottom) + 16px);
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		flex-direction: column;
		gap: 8px;
		z-index: 200;
		width: calc(100% - 48px);
		max-width: calc(var(--maxw) - 48px);
		pointer-events: none;
	}
	.toast {
		background: rgba(25, 31, 40, 0.92);
		color: #fff;
		font-size: 14px;
		font-weight: 500;
		padding: 13px 18px;
		border-radius: var(--r-btn);
		text-align: center;
		animation: rise 0.25s cubic-bezier(0.22, 1, 0.36, 1) both;
	}
</style>
