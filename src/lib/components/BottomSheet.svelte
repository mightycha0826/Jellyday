<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = $bindable(false),
		title = '',
		children
	}: { open?: boolean; title?: string; children: Snippet } = $props();

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') open = false;
	}
</script>

<svelte:window onkeydown={onKey} />

{#if open}
	<div class="dim" onclick={() => (open = false)} aria-hidden="true"></div>
	<div class="sheet" role="dialog" aria-modal="true" aria-label={title || '시트'}>
		<div class="grip" aria-hidden="true"></div>
		{#if title}<h2>{title}</h2>{/if}
		<div class="body">
			{@render children()}
		</div>
	</div>
{/if}

<style>
	.dim {
		position: fixed;
		inset: 0;
		background: rgba(0, 23, 51, 0.45);
		z-index: 90;
		animation: fade 0.2s both;
	}
	.sheet {
		position: fixed;
		bottom: 0;
		left: 50%;
		transform: translateX(-50%);
		width: 100%;
		max-width: var(--maxw);
		max-height: 88dvh;
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-radius: 24px 24px 0 0;
		box-shadow: var(--shadow-sheet);
		padding: 8px var(--pad) calc(env(safe-area-inset-bottom) + 20px);
		z-index: 91;
		animation: up 0.32s cubic-bezier(0.22, 1, 0.36, 1) both;
	}
	.grip {
		width: 40px;
		height: 4px;
		border-radius: 2px;
		background: var(--fill-strong);
		margin: 6px auto 14px;
		flex: none;
	}
	h2 {
		font-size: 20px;
		font-weight: 700;
		margin-bottom: 16px;
		flex: none;
	}
	.body {
		overflow-y: auto;
		min-height: 0;
	}
	@keyframes fade {
		from {
			opacity: 0;
		}
	}
	@keyframes up {
		from {
			transform: translateX(-50%) translateY(100%);
		}
	}
</style>
